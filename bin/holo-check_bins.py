#16.04.2020 - Holoflow 0.1.

import subprocess
import argparse
import time
import os
import sys


#Argument parsing
parser = argparse.ArgumentParser(description='Runs holoflow pipeline.')
parser.add_argument('-binning_dir', help="binning directory", dest="binning_dir", required=True)
parser.add_argument('-check_mtb', help="empty check file", dest="check_mtb", required=True)
parser.add_argument('-check_mxb', help="empty check file", dest="check_mxb", required=True)
#parser.add_argument('--check_vmb', help="empty check file", dest="check_vmb")
parser.add_argument('--check_cct', help="concoct check if empty", dest="check_cct")
parser.add_argument('-ID', help="ID", dest="ID", required=True)
parser.add_argument('-log', help="pipeline log file", dest="log", required=True)
args = parser.parse_args()


binning_dir=args.binning_dir
check_mxb=args.check_mxb
check_mtb=args.check_mtb
ID=args.ID
log=args.log

##############################################
#################### WRITE TO LOG ##########################
##############################################

true_bins=list()
dim_trueb=list() #diminutive
false_bins=list()
dim_falseb=list()
final_check=binning_dir+'/'+ID+'_checked_bins.txt'

######## Coassembly
if args.check_cct:
    with open(check_mxb,'r') as mxb, open(check_mtb,'r') as mtb, open(args.check_cct,'r') as cct:
# open(args.check_vmb,'r') as vmb,
        # Read whether it is True: there are bins or it is False: there are no bins
        check=list()
        check.append(mxb.readline())
        check.append(mtb.readline())
        check.append(cct.readline())
#        check.append(vmb.readline())


        for binner in check:
            if 'True' in binner:
                binner=binner.split(' ')
                true_bins.append(binner[1])
                dim_trueb.append(binner[2])

            if 'False' in binner:
                binner=binner.split(' ')
                false_bins.append(binner[1])
                dim_falseb.append(binner[2])

        # All binners generated bins, nothing to do
        if len(false_bins) == 0:
            os.remove(check_mxb)
            os.remove(check_mtb)
            os.remove(args.check_cct)
#            os.remove(args.check_vmb)
            os.mknod(final_check)
            pass

        # Some of all the  binners did not generate bins
        else:
            # At least one binner generated bins, continue
            if len(true_bins) >= 1:
                t_binner=true_bins[0]   # true bins are those binners that generated bins, false those which did not
                dim_tb=dim_trueb[0].strip()
                t_bintable=binning_dir+'/'+ID+'.bins_'+t_binner+'.txt'
                t_bindir=binning_dir+'/'+ID+'_'+t_binner

                for i in range(len(false_bins)): # for those binners without bins, duplicate data in other binner
                    f_binner=false_bins[i]
                    dim_fb=dim_falseb[i].strip()
                    f_bintable=binning_dir+'/'+ID+'.bins_'+f_binner+'.txt'
                    f_bindir=binning_dir+'/'+ID+'_'+f_binner

                    # Duplicate bin table
                    if (not os.path.isfile(f_bintable)) or os.path.getsize(f_bintable) == 0:
                        cp_btCmd='cp '+t_bintable+' '+f_bintable+'.tmp && grep '+str(dim_tb)+' '+f_bintable+'.tmp | sed s/'+dim_tb+'/'+dim_fb+'/ > '+f_bintable+' && rm '+f_bintable+'.tmp'
                        subprocess.Popen(cp_btCmd,shell=True).wait()

                    # Duplicate bin directory
                    # Remove if exists, because it will be empty, Duplicate and rename
                    if os.path.exists(f_bindir):
                        mv_bdCmd='mv '+f_bindir+' '+f_bindir+'_remove && cp -r '+t_bindir+' '+f_bindir+' && for f in '+f_bindir+'/*'+str(dim_tb)+'* ; do mv "$f" "$(echo "$f" | sed s/'+str(dim_tb)+'/'+str(dim_fb)+'/)"; done'
                        subprocess.Popen(mv_bdCmd,shell=True).wait()

                        with open(log,'a+') as log_dup:
                            log_dup.write('\n\t\t'+f_binner+' did not produce any bins originally, the observed bins are duplicates from '+t_binner+'.\n')
                            sys.exit()

                        # Check and finish
                        if (not len(os.listdir(f_bindir)) == 0) and (f_binner == false_bins[-1]):
                            os.mknod(final_check)


            # No bins were generated at all
            if len(true_bins) == 0:
                with open(log,'a+') as log_file:
                    log_file.write('\n\n\n\t\t\tNo bins were generated by any binner, DASTool merging will not be possible\n\n\n')
                    sys.exit()



######## Individual assembly
else:
    with open(check_mxb,'r') as mxb, open(check_mtb,'r') as mtb:

        # Read whether it is True: there are bins or it is False: there are no bins
        check=list()
        check.append(mxb.readline())
        check.append(mtb.readline())

        for binner in check:
            if 'True' in binner:
                binner=binner.split(' ')
                true_bins.append(binner[1])
                dim_trueb.append(binner[2])

            if 'False' in binner:
                binner=binner.split(' ')
                false_bins.append(binner[1])
                dim_falseb.append(binner[2])

        # All binners generated bins, nothing to do
        if len(false_bins) == 0:
            os.remove(check_mxb)
            os.remove(check_mtb)
            os.mknod(final_check)
            pass

        # Some of all the  binners did not generate bins
        else:
            # At least one binner generated bins
            if len(true_bins) >= 1:
                t_binner=true_bins[0]
                dim_tb=dim_trueb[0].strip()
                t_bintable=binning_dir+'/'+ID+'.bins_'+t_binner+'.txt'
                t_bindir=binning_dir+'/'+ID+'_'+t_binner

                for i in range(len(false_bins)):
                    f_binner=false_bins[i]
                    dim_fb=dim_falseb[i].strip()
                    f_bintable=binning_dir+'/'+ID+'.bins_'+f_binner+'.txt'
                    f_bindir=binning_dir+'/'+ID+'_'+f_binner

                    # Duplicate bin table
                    if (not os.path.isfile(f_bintable)) or os.path.getsize(f_bintable) == 0:
                        cp_btCmd='cp '+t_bintable+' '+f_bintable+'.tmp && grep '+str(dim_tb)+' '+f_bintable+'.tmp | sed s/'+dim_tb+'/'+dim_fb+'/ > '+f_bintable+' && rm '+f_bintable+'.tmp'
                        subprocess.Popen(cp_btCmd,shell=True).wait()

                    # Duplicate bin directory
                    # Remove if exists, because it will be empty, Duplicate and rename
                    if os.path.exists(f_bindir):
                        mv_bdCmd='mv '+f_bindir+' '+f_bindir+'_remove && cp -r '+t_bindir+' '+f_bindir+' && for f in '+f_bindir+'/*'+str(dim_tb)+'* ; do mv "$f" "$(echo "$f" | sed s/'+str(dim_tb)+'/'+str(dim_fb)+'/)"; done'
                        subprocess.Popen(mv_bdCmd,shell=True).wait()

                        with open(log,'a+') as log_dup:
                            log_dup.write('\n\t\t'+f_binner+' did not produce any bins originally, the observed bins are duplicates from '+t_binner+'.\n')
                            sys.exit()


                        # Check and finish
                        if (not len(os.listdir(f_bindir)) == 0) and (f_binner == false_bins[-1]):
                            os.mknod(final_check)


            # No bins were generated at all
            if len(true_bins) == 0:
                with open(log,'a+') as log_file:
                    log_file.write('\n\n\n\t\t\tNo bins were generated by any binner, DASTool merging will not be possible\n\n\n')
                    sys.exit()
