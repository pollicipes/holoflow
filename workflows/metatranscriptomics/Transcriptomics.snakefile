################################################################################
################################################################################
################################################################################
# Snakefile for metatranscriptomics
# Raphael Eisenhofer 29/11/2021
#
################################################################################
################################################################################
################################################################################

### Setup sample wildcard:
import os
from glob import glob

SAMPLE = [os.path.basename(fn).replace("_1.fastq.gz", "")
            for fn in glob(f"2_Reads/0_Untrimmed/*_1.fastq.gz")]

print("Detected the following samples:")
print(SAMPLE)
################################################################################
### Setup the desired outputs
rule all:
    input:
        "3_Outputs/2_rRNA_Mapping/coverM_RNA_mapping.txt",
        "3_Outputs/3_MAG_Gene_Mapping/coverM_per_gene.txt",
        "3_Outputs/3_MAG_Gene_Mapping/coverM_overall_mapping.txt"
################################################################################
### Filter reads with fastp
rule fastp:
    input:
        r1i = "2_Reads/0_Untrimmed/{sample}_1.fastq.gz",
        r2i = "2_Reads/0_Untrimmed/{sample}_2.fastq.gz"
    output:
        r1o = temp("2_Reads/1_Trimmed/{sample}_trimmed_1.fastq.gz"),
        r2o = temp("2_Reads/1_Trimmed/{sample}_trimmed_2.fastq.gz"),
        fastp_html = "2_Reads/2_fastp_reports/{sample}.html",
        fastp_json = "2_Reads/2_fastp_reports/{sample}.json"
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        10
    benchmark:
        "3_Outputs/0_Logs/{sample}_fastp.benchmark.tsv"
    log:
        "3_Outputs/0_Logs/{sample}_fastp.log"
    message:
        "Using FASTP to trim adapters and low quality sequences for {wildcards.sample}"
    shell:
        """
        fastp \
            --in1 {input.r1i} --in2 {input.r2i} \
            --out1 {output.r1o} --out2 {output.r2o} \
            --trim_poly_g \
            --trim_poly_x \
            --n_base_limit 5 \
            --qualified_quality_phred 20 \
            --length_required 60 \
            --thread {threads} \
            --html {output.fastp_html} \
            --json {output.fastp_json} \
            --adapter_sequence CTGTCTCTTATACACATCT \
            --adapter_sequence_r2 CTGTCTCTTATACACATCT \
        &> {log}
        """
################################################################################
## Index host genomes:
# rule index_ref:
#     input:
#         "1_References"
#     output:
#         bt2_index = "1_References/CattedRefs.fna.gz.rev.2.bt2l",
#         catted_ref = "1_References/CattedRefs.fna.gz"
#     conda:
#         "1_QC.yaml"
#     threads:
#         40
#     log:
#         "3_Outputs/0_Logs/host_genome_indexing.log"
#     message:
#         "Concatenating and indexing host genomes with Bowtie2"
#     shell:
#         """
#         # Concatenate input reference genomes
#         cat {input}/*.gz > {input}/CattedRefs.fna.gz
#
#         # Index catted genomes
#         bowtie2-build \
#             --large-index \
#             --threads {threads} \
#             {output.catted_ref} {output.catted_ref} \
#         &> {log}
#         """
################################################################################
### Map to host reference genome using STAR
rule STAR_host_mapping:
    input:
        r1i = "2_Reads/1_Trimmed/{sample}_trimmed_1.fastq.gz",
        r2i = "2_Reads/1_Trimmed/{sample}_trimmed_2.fastq.gz"
    output:
        non_host_r1 = "3_Outputs/1_Host_Mapping/{sample}_non_host_1.fastq.gz",
        non_host_r2 = "3_Outputs/1_Host_Mapping/{sample}_non_host_2.fastq.gz",
        host_bam = "3_Outputs/1_Host_Mapping/{sample}_host.bam"
    params:
        r1rn = "3_Outputs/1_Host_Mapping/{sample}_non_host_1.fastq",
        r2rn = "3_Outputs/1_Host_Mapping/{sample}_non_host_2.fastq",
        gene_counts = "3_Outputs/1_Host_Mapping/{sample}_read_counts.tsv",
        sj = "3_Outputs/1_Host_Mapping/{sample}_SJ.tsv",
        host_genome = "/home/projects/ku-cbd/people/antalb/holofood/chicken_transcriptomics/genome",
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        40
    benchmark:
        "3_Outputs/0_Logs/{sample}_host_mapping.benchmark.tsv"
    log:
        "3_Outputs/0_Logs/{sample}_host_mapping.log"
    message:
        "Mapping {wildcards.sample} to host genome using STAR"
    shell:
        """
        # Map reads to host genome using STAR
        STAR \
            --runMode alignReads \
            --runThreadN {threads} \
            --genomeDir {params.host_genome} \
            --readFilesIn {input.r1i} {input.r2i} \
            --outFileNamePrefix {wildcards.sample} \
            --outSAMtype BAM Unsorted \
            --outReadsUnmapped Fastx \
            --readFilesCommand zcat \
            --quantMode GeneCounts \
        &> {log}

        # Rename files
        mv {wildcards.sample}Aligned.out.bam {output.host_bam}
        mv {wildcards.sample}ReadsPerGene.out.tab {params.gene_counts}
        mv {wildcards.sample}SJ.out.tab {params.sj}
        mv {wildcards.sample}Unmapped.out.mate1 {params.r1rn}
        mv {wildcards.sample}Unmapped.out.mate2 {params.r2rn}

        # Compress non-host reads
        pigz \
            -p {threads} \
            {params.r1rn}

        pigz \
            -p {threads} \
            {params.r2rn}

        # Clean up unwanted outputs
        rm -r {wildcards.sample}_STARtmp
        rm {wildcards.sample}*out*
        """
################################################################################
## Index rRNA, tRNA databases:
rule index_RNA:
    input:
        "1_References/Catted_rRNA_tRNA_db.fna.gz"
    output:
        bt2_index = "1_References/Catted_rRNA_tRNA_db.fna.gz.rev.2.bt2l",
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        40
    log:
        "3_Outputs/0_Logs/MAG_genes_bowtie2_indexing.log"
    message:
        "Indexing MAG catalogue with Bowtie2"
    shell:
        """
        # Index MAG gene catalogue
        bowtie2-build \
            --large-index \
            --threads {threads} \
            {input} {input} \
        &> {log}
        """
################################################################################
### Map non-host reads to DRAM genes files using Bowtie2
rule bowtie2_RNA_mapping:
    input:
        non_host_r1 = "3_Outputs/1_Host_Mapping/{sample}_non_host_1.fastq.gz",
        non_host_r2 = "3_Outputs/1_Host_Mapping/{sample}_non_host_2.fastq.gz",
        bt2_index = "1_References/Catted_rRNA_tRNA_db.fna.gz.rev.2.bt2l"
    output:
        non_rna_r1 = "3_Outputs/2_rRNA_Mapping/{sample}_non_ribo_1.fastq.gz",
        non_rna_r2 = "3_Outputs/2_rRNA_Mapping/{sample}_non_ribo_2.fastq.gz",
        all_bam = temp("3_Outputs/2_rRNA_Mapping/{sample}.bam"),
        rna_bam = "3_Outputs/2_rRNA_Mapping/{sample}_rna.bam"
    params:
        RNAdb = "1_References/Catted_rRNA_tRNA_db.fna.gz"
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        20
    benchmark:
        "3_Outputs/0_Logs/{sample}_RNAdb_mapping.benchmark.tsv"
    log:
        "3_Outputs/0_Logs/{sample}_RNAdb_mapping.log"
    message:
        "Mapping {wildcards.sample} to RNA db using Bowtie2"
    shell:
        """
        # Map reads to RNAdb using Bowtie2
        bowtie2 \
            --time \
            --threads {threads} \
            -x {params.RNAdb} \
            -1 {input.non_host_r1} \
            -2 {input.non_host_r2} \
            --seed 1337 \
        | samtools sort -@ {threads} -o {output.all_bam} -

        # Filter out only RNA hits
        samtools view -b -@ {threads} -F4 {output.all_bam} -o {output.rna_bam}


        # Export unmapped reads (non-RNA)
        samtools view -b -@ {threads} -f12 {output.all_bam} \
        | samtools fastq -@ {threads} -1 {output.non_rna_r1} -2 {output.non_rna_r2} -
        &> {log}
        """
################################################################################
### Calculate the number of reads that mapped to RNA db with CoverM
rule coverM_RNA_genes:
    input:
        expand("3_Outputs/2_rRNA_Mapping/{sample}.bam", sample=SAMPLE),
    output:
        total_cov = "3_Outputs/2_rRNA_Mapping/coverM_RNA_mapping.txt"
    params:
        rna_ref = "1_References/Catted_rRNA_tRNA_db.fna.gz",
        rna_ref_dc = "1_References/Catted_rRNA_tRNA_db.fna"
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        40
    message:
        "Calculating RNA mapping rate using CoverM"
    shell:
        """
        # Decompress reference
        gunzip {params.rna_ref}

        # Get overall mapping rate
        coverm genome \
            -b {input} \
            --genome-fasta-files {params.rna_ref_dc} \
            -m relative_abundance \
            -t {threads} \
            --min-covered-fraction 0 \
            > {output.total_cov}

        # Compress reference
        pigz -t 40 {params.rna_ref_dc}
        """
################################################################################
## Index MAGs:
rule index_MAGs:
    input:
        "1_References/genes.fna.gz"
    output:
        bt2_index = "1_References/MAG_genes.fna.gz.rev.2.bt2l",
        MAG_genes = "1_References/MAG_genes.fna.gz"
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        40
    log:
        "3_Outputs/0_Logs/MAG_genes_bowtie2_indexing.log"
    message:
        "Indexing MAG catalogue with Bowtie2"
    shell:
        """
        # Rename MAG gene catalogue
        mv {input} {output.MAG_genes}

        # Index MAG gene catalogue
        bowtie2-build \
            --large-index \
            --threads {threads} \
            {output.MAG_genes} {output.MAG_genes} \
        &> {log}
        """
################################################################################
### Map non-host reads to DRAM genes files using Bowtie2
rule bowtie2_MAG_mapping:
    input:
        non_ribo_r1 = "3_Outputs/2_rRNA_Mapping/{sample}_non_ribo_1.fastq.gz",
        non_ribo_r2 = "3_Outputs/2_rRNA_Mapping/{sample}_non_ribo_2.fastq.gz",
        bt2_index = "1_References/MAG_genes.fna.gz.rev.2.bt2l"
    output:
        bam = "3_Outputs/3_MAG_Gene_Mapping/{sample}.bam"
    params:
        MAG_genes = "1_References/MAG_genes.fna.gz"
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        20
    benchmark:
        "3_Outputs/0_Logs/{sample}_MAG_genes_mapping.benchmark.tsv"
    log:
        "3_Outputs/0_Logs/{sample}_MAG_genes_mapping.log"
    message:
        "Mapping {wildcards.sample} to MAG genes using Bowtie2"
    shell:
        """
        # Map reads to MAGs using Bowtie2
        bowtie2 \
            --time \
            --threads {threads} \
            -x {params.MAG_genes} \
            -1 {input.non_ribo_r1} \
            -2 {input.non_ribo_r2} \
            --seed 1337 \
        | samtools sort -@ {threads} -o {output.bam} \
        &> {log}
        """
################################################################################
### Calculate the number of reads that mapped to MAG catalogue genes with CoverM
rule coverM_MAG_genes:
    input:
        expand("3_Outputs/3_MAG_Gene_Mapping/{sample}.bam", sample=SAMPLE),
    output:
        gene_counts = "3_Outputs/3_MAG_Gene_Mapping/coverM_per_gene.txt",
        total_cov = "3_Outputs/3_MAG_Gene_Mapping/coverM_overall_mapping.txt"
    params:
    conda:
        "Transcriptomics_conda.yaml"
    threads:
        40
    message:
        "Calculating MAG gene mapping rate using CoverM"
    shell:
        """
        # Get overall mapping rate
        coverm genome \
            -b {input} \
            -s _ \
            -m relative_abundance \
            -t {threads} \
            --min-covered-fraction 0 \
            > {output.total_cov}

        # Get counts to specific genes too:
        coverm contig \
            -b {input} \
            -m count \
            -t {threads} \
            --proper-pairs-only \
            > {output.gene_counts}
        """
