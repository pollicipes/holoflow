import argparse
import subprocess
import os
import sys

###########################
#Argument parsing
###########################
# Gather input files and variables from command line
parser = argparse.ArgumentParser(description='Runs holoflow pipeline.')
parser.add_argument('-f', help="input.txt file", dest="input_txt", required=True)
parser.add_argument('-d', help="temp files directory path", dest="work_dir", required=True)
parser.add_argument('-c', help="config file", dest="config_file", required=False)
parser.add_argument('-g', help="reference genome path or path to .tar.gz data base", dest="ref", required=False)
parser.add_argument('-adapter1', help="adapter 1 sequence", dest="adapter1", required=False)
parser.add_argument('-adapter2', help="adapter 2 sequence", dest="adapter2", required=False)
parser.add_argument('-k', help="keep tmp directories", dest="keep", action='store_true')
parser.add_argument('-l', help="pipeline log file", dest="log", required=False)
parser.add_argument('-t', help="threads", dest="threads", required=True)
parser.add_argument('-N', help="JOB ID", dest="job", required=True)
parser.add_argument('-W', help="rewrite everything", dest="REWRITE", action='store_true')
args = parser.parse_args()

in_f=args.input_txt
path=args.work_dir
ref=args.ref
adapter1=args.adapter1
adapter2=args.adapter2
cores=args.threads
job=args.job

    # retrieve current directory
file = os.path.dirname(sys.argv[0])
curr_dir = os.path.abspath(file)

# If the user does not specify a config file, provide default file in GitHub
if not (args.config_file):
    cpconfigCmd= 'cp '+curr_dir+'/workflows/preprocessing/config.yaml '+path+'/'+job+'_config.yaml'
    subprocess.Popen(cpconfigCmd,shell=True).wait()

    config = path+'/'+job+'_config.yaml'
else:
    config=args.config_file

# If the user does not specify a log file, provide default path
if not (args.log):
    log = os.path.join(path,"Holoflow_preprocessing.log")
else:
    log=args.log

    # Load dependencies
loaddepCmd='module unload gcc && module load tools anaconda3/4.4.0'
subprocess.Popen(loaddepCmd,shell=True).wait()


    #Append variables to .yaml config file for Snakefile calling standalone files
import ruamel.yaml
yaml = ruamel.yaml.YAML() # create yaml obj
yaml.explicit_start = True
with open(str(config), 'r') as config_file:
    data = yaml.load(config_file) # get data found now in config - as dictionary
    if data == None: # if config is empty, create dictionary
        data = {}

with open(str(config), 'w') as config_file:
    data['holopath'] = str(curr_dir)
    data['logpath'] = str(log)
    data['threads'] = str(cores)
    data['adapter1'] = str(adapter1)
    data['adapter2'] = str(adapter2)

    # Retrieve reference genome file from .tar.gz dir generated by preparegenomes.py
    if str(ref).endswith('.tar.gz'):
        if not os.path.exists(path+'/PRG'):
            decompCmd='mkdir '+path+'/PRG && tar -xzvf '+ref+' -C '+path+'/PRG'
            subprocess.Popen(decompCmd,shell=True).wait()
        else:
            decompCmd='tar -xzvf '+ref+' -C '+path+'/PRG'
            subprocess.Popen(decompCmd,shell=True).wait()

        ref_ID = os.path.basename(ref).replace('.tar.gz','')
        ref = path+'/PRG/'+ref_ID+'.fna'
        data['refgenomes'] = str(ref)
    else:
        data['refgenomes'] = str(ref)


    dump = yaml.dump(data, config_file) # load updated dictionary to config file


###########################
## Functions
###########################



    ###########################
    ###### PREPROCESSING FUNCTIONS

def in_out_preprocessing(path,in_f):
    """Generate output names files from input.txt. Rename and move
    input files where snakemake expects to find them if necessary."""
    # Define general input directory and create it if not exists "00-InputData"
    in_dir_0 = os.path.join(path,"PPR_00-InputData")


    with open(in_f,'r') as in_file:
        all_lines = in_file.readlines() # Read input.txt lines
        # remove empty lines
        all_lines = map(lambda s: s.strip(), all_lines)
        lines = list(filter(None, list(all_lines))) # save input file content withput blank lines in "lines"

    # Define variables
    output_files=''
    final_temp_dir="PPR_03-MappedToReference"


    if os.path.exists(in_dir_0):  # Already run for: same job (wants to continue/Rewrite), for another job

        # Define specific job dir
        in_dir=in_dir_0+'/'+job
        # Define specific job final output dir - for snakemake (needs output files)
        final_temp_dir=final_temp_dir+'/'+job

        if args.REWRITE:    # If user wants to remove previous runs' data and run from scratch
            if os.path.exists(in_dir):
                rmCmd='rm -rf '+in_dir+''
                subprocess.Popen(rmCmd,shell=True).wait()

        if not os.path.exists(in_dir) or args.REWRITE: # if job input directory does not exist
            os.makedirs(in_dir)

        else: # already exists and don't want to rewrite, then pass
            pass


        # If job input directory is empty, do all - otherwise, just save output names for snakemake calling
        if len(os.listdir(in_dir) ) == 0:

            for line in lines: # for line in lines in input file, do:
                ### Skip line if starts with # (comment line)
                if not (line.startswith('#')):

                    line = line.strip('\n').split(' ') # Create a list of each line
                    # define variables
                    sample_name=line[0]
                    in_for=line[1] # input for (read1) file
                    in_rev=line[2] # input reverse (read2) file

                    #Define output files based on input.txt for snakemake
                    output_files+=path+'/'+final_temp_dir+'/'+sample_name+'_1.fastq.gz '
                    output_files+=path+'/'+final_temp_dir+'/'+sample_name+'_2.fastq.gz '


                    # Define specific input file for the Snakefile -> create standardized input from user's
                    in1=in_dir+'/'+sample_name+'_1.fastq.tmp.gz'
                    # Check if input files already in desired/standard input dir
                    if os.path.isfile(in1):
                        pass
                    else:
                        #If the file is not in the working directory, create soft link in it
                        if (not (os.path.isfile(in1)) and os.path.isfile(in_for)):
                            if in_for.endswith('.gz'): # if compressed, decompress in standard dir with std ID
                                read1Cmd = 'ln -s '+in_for+' '+in1+''
                                subprocess.Popen(read1Cmd, shell=True).wait()
                            else:
                                read1Cmd = 'gzip -c '+in_for+' > '+in1+''
                                subprocess.Popen(read1Cmd, shell=True).wait()


                    # Define input file
                    in2=in_dir+'/'+sample_name+'_2.fastq.tmp.gz'
                    # Check if input files already in desired dir
                    if os.path.isfile(in2):
                        pass
                    else:
                        #If the file is not in the working directory, transfer it
                        if (not (os.path.isfile(in2)) and os.path.isfile(in_rev)):
                            if in_for.endswith('.gz'):
                                read2Cmd = 'ln -s '+in_rev+' '+in2+''
                                subprocess.Popen(read2Cmd, shell=True).wait()
                            else:
                                read2Cmd = 'gzip -c '+in_rev+' > '+in2+''
                                subprocess.Popen(read2Cmd, shell=True).wait()


                    # Add stats and bam output files only once per sample
                    output_files+=(path+"/"+final_temp_dir+"/"+sample_name+".stats ")
                    output_files+=(path+"/"+final_temp_dir+"/"+sample_name+"_ref.bam ")


        else: # the input directory already exists and is full, don't want to create it again, just re-run from last step
            for line in lines:
                ### Skip line if starts with # (comment line)
                if not (line.startswith('#')):

                    line = line.strip('\n').split(' ') # Create a list of each line
                    sample_name=line[0]
                    in_for=line[1]
                    in_rev=line[2]

                    # Define output files based on input.txt
                    output_files+=path+'/'+final_temp_dir+'/'+sample_name+'_1.fastq.gz '
                    output_files+=path+'/'+final_temp_dir+'/'+sample_name+'_2.fastq.gz '

                    # Add stats and bam output files only once per sample
                    output_files+=(path+"/"+final_temp_dir+"/"+sample_name+".stats ")
                    output_files+=(path+"/"+final_temp_dir+"/"+sample_name+"_ref.bam ")



    if not os.path.exists(in_dir_0): # IF IT DOES NOT EXIST, start from 0 - never run before
            os.makedirs(in_dir_0) # create general input directory

            # Define sent job dir
            in_dir=in_dir_0+'/'+job
            final_temp_dir=final_temp_dir+'/'+job
            os.makedirs(in_dir) # create specific job directory

            # Do everything
            for line in lines:
                ### Skip line if starts with # (comment line)
                if not (line.startswith('#')):

                    line = line.strip('\n').split(' ') # Create a list of each line
                    sample_name=line[0]
                    in_for=line[1]
                    in_rev=line[2]

                    # Define output files based on input.txt
                    output_files+=path+'/'+final_temp_dir+'/'+sample_name+'_1.fastq.gz '
                    output_files+=path+'/'+final_temp_dir+'/'+sample_name+'_2.fastq.gz '


                    # Define input file
                    in1=in_dir+'/'+sample_name+'_1.fastq.tmp.gz'
                    # Check if input files already in desired dir
                    if os.path.isfile(in1):
                        pass
                    else:
                        #If the file is not in the working directory, create soft link in it
                        if (not (os.path.isfile(in1)) and os.path.isfile(in_for)):
                            if in_for.endswith('.gz'): # if compressed, decompress in standard dir with std ID
                                read1Cmd = 'ln -s '+in_for+' '+in1+''
                                subprocess.Popen(read1Cmd, shell=True).wait()
                            else:
                                read1Cmd = 'gzip -c '+in_for+' > '+in1+''
                                subprocess.Popen(read1Cmd, shell=True).wait()


                    # Define input file
                    in2=in_dir+'/'+sample_name+'_2.fastq.tmp.gz'
                    # Check if input files already in desired dir
                    if os.path.isfile(in2):
                        pass
                    else:
                        #If the file is not in the working directory, transfer it
                        if (not (os.path.isfile(in2)) and os.path.isfile(in_rev)):
                            if in_for.endswith('.gz'):
                                read2Cmd = 'ln -s '+in_rev+' '+in2+''
                                subprocess.Popen(read2Cmd, shell=True).wait()
                            else:
                                read2Cmd = 'gzip -c '+in_rev+' > '+in2+''
                                subprocess.Popen(read2Cmd, shell=True).wait()


                    # Add stats and bam output files only once per sample
                    output_files+=(path+"/"+final_temp_dir+"/"+sample_name+".stats ")
                    output_files+=(path+"/"+final_temp_dir+"/"+sample_name+"_ref.bam ")


    return output_files



def run_preprocessing(in_f, path, config, cores):
    """Run snakemake on shell, wait for it to finish.
    Given flag, decide whether keep only last directory."""

    # Define output names
    out_files = in_out_preprocessing(path,in_f) # obtain output files from function as string
    curr_dir = os.path.dirname(sys.argv[0])
    holopath = os.path.abspath(curr_dir)
    path_snkf = os.path.join(holopath,'workflows/preprocessing/Snakefile')

    # Run snakemake
    log_file = open(str(log),'w+')
    log_file.write("Have a nice run!\n\t\tHOLOFLOW Preprocessing starting\n")
    log_file.close()

    # call snakemake from terminal with subprocess package
    prep_snk_Cmd = 'module load tools anaconda3/4.4.0 && snakemake -s '+path_snkf+' -k '+out_files+' --configfile '+config+' --cores '+cores+''
    subprocess.Popen(prep_snk_Cmd, shell=True).wait()

    log_file = open(str(log),'a+')
    log_file.write("\n\t\tHOLOFLOW Preprocessing has finished :)\n")
    log_file.close()

    # Keep temporary directories - not the last one -  / or remove them
    if args.keep: # If -k, True: keep
        pass
    else: # If not -k, keep only last dir
        exist=list()
        for file in out_files.split(" "):
            exist.append(os.path.isfile(file))

        if all(exist): # all output files exist
            rmCmd='cd '+path+' | grep -v '+final_temp_dir+' | xargs rm -rf && mv '+final_temp_dir+' PPR_Holoflow'
            subprocess.Popen(rmCmd,shell=True).wait()

        else:   # all expected output files don't exist: keep tmp dirs
            log_file = open(str(log),'a+')
            log_file.write("Looks like something went wrong...\n\t\t The temporal directories have been kept, you should have a look...")
            log_file.close()




###########################
#### Workflows running
###########################


# 1    # Preprocessing workflow
run_preprocessing(in_f, path, config, cores)
