#!/usr/bin/python -O

#Calculate coverage from raw file

import sys
import os
import datetime
import getopt
#import libs.joblib
from site import addsitedir

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

addsitedir(os.path.join(__location__, 'libs'))

from joblib import Parallel, delayed
from math import pow;
#profile = []
#insertions = {}
config = {}
total_contigs = 0

def read_genome(filename):
    res_seq = []

    seq =''
    for line in open(filename):
        if line[0] == '>':
            res_seq.append(line[1:])
        else:
            seq += line.strip()
    res_seq.append(seq)
    return res_seq


def read_contigs(filename):
    res_seq = {}

    seq =''
    cont_name = ''
    for line in open(filename):
        if line[0] == '>':
            if cont_name != '':
                res_seq[cont_name] = seq
            seq = ''
            cont_name = line[1:].strip()
        else:
            seq += line.strip()
    if cont_name != '':
        res_seq[cont_name] = seq
    return res_seq


def write_fasta(data, filename):
    outFile = open(filename, 'w')
    for seq in data:
            outFile.write('>' + seq[0].strip() + '\n' );
            i = 0
            while i < len(seq[1]):
                    outFile.write(seq[1][i:i+60] + '\n')
                    i += 60
    outFile.close()


def vote_insertions(position, insertions):
#    global insertions;
    arr = insertions[position]
    lengths = {}
    for strn in arr:
        if len(strn) not in lengths:
            lengths[len(strn)] = 0;
        lengths[len(strn)] += 1;
    opt_len = 0;
    max = 0;
    for l in lengths:
        if lengths[l] > max:
            max = lengths[l]
            opt_len = l;
#    print "insertion; length =" + str(opt_len)
    ins_profile = []
    for i in range (0, opt_len):
        ins_profile.append({})
        for j in ('A','C','T','G','N'):
            ins_profile[i][j] = 0;
    for strn in arr:
#Others are ignored
        if len(strn) == opt_len:
            for i in range (0, opt_len):
                ins_profile[i][strn[i]]+=1;
    best_ins = ''
    for i in range (0, opt_len):
        next_nucl = 'N';
        for j in ('A','C','T','G'):
            if ins_profile[i][j] > ins_profile [i][next_nucl]:
                next_nucl = j;
        best_ins += next_nucl;
    return best_ins


def process_read(arr, l,m, profile, insertions):
#    global profile
#    global insertions
    cigar = arr[5]
    aligned = arr[9];
    qual_aligned = arr[10]
    position = int(arr[3]) - 1
    map_q = int(arr[4]);
    mate = m;
    l_read = len(aligned);

    if '*' in cigar:
        return 0;


    if config["use_quality"]:
        mate *=  (1 - pow(10,map_q/-10))
    shift = 0;
    nums = []
    operations = []
    tms = "";
    aligned_length = 0;
    for i in range(0, len(cigar)):

        if cigar[i].isdigit():
             tms += cigar[i]
        else:
            nums.append(int(tms));
            operations.append(cigar[i]);
            if cigar[i]=='M':
                aligned_length += int(tms)
            tms = ''
#we do not need short reads aligned near gaps
    if aligned_length < min(l_read* 0.4, 40) and position > l_read/2 and l - position > l_read/2 and mate == 1:
        return 0;
    state_pos = 0;
    shift = 0;
    skipped = 0;
    deleted = 0;
#    if position < 150:
#        print aligned+ " "+ cigar +" " + str(position)
    insertion_string = ''
    int_A = ord('A') - 1
    for i in range(0, l_read):
    #            print aligned[i];
    #            print profile[i+position - 1]
        if i + position - skipped >= l:
#            print str(i) +" " + str(position) + " " + str(skipped)+ " " + str(l_read) + " " + cigar +" " + str(l) + " " + insertion_string + "  " + operations[state_pos]
#            print "read going out of contig"
            break;

        if shift + nums[state_pos] <= i:
            shift += nums[state_pos]
            state_pos += 1
#        if position == 698:
#            print operations[state_pos]
        if insertion_string != '' and operations[state_pos] != 'I':
#            print "inserting" + str(i) +" " + str(position) + " " + str(skipped)+ " " + str(l_read) + " " + cigar +" " + str(l) + " " + insertion_string + "  " + operations[state_pos]
            ind = i+position-skipped - 1;
            if ind not in insertions:
                insertions[ind]= []
            insertions[ind].append(insertion_string)
            insertion_string = ''
        if operations[state_pos] == 'M':
            if i +  position - skipped < l:
                t_mate = mate;
                if config["use_quality"]:
                    k = pow(10, (ord(qual_aligned[i - deleted]) - int_A ) /-10);
                    if qual_aligned[i - deleted] == 'B':
                        t_mate *= 0.2
                    else:
                        t_mate = t_mate * (1 - k/(k+1))
                profile[i+position -skipped][aligned[i - deleted]] += t_mate
        else:
            if  operations[state_pos] in ('S', 'I', 'H'):
                if operations[state_pos] == 'I':
                    if insertion_string == '':
                        profile[i+position -skipped - 1 ]['I'] += mate
                    insertion_string += (aligned[i])
                skipped += 1;
            elif operations[state_pos] == 'D':
#               print str(i) +" " + str(position) + " " + str(skipped)+ " " + str(l_read) + " " + cigar +" " + str(l) + " " + insertion_string + "  " + operations[state_pos]
#                print str(i) + " " + str(i+position - skipped) + "    deletion!"
                profile[i+position - skipped]['D'] += mate
#                skipped =1;
#                shift -= 1;
                deleted += 1;
    if insertion_string != '' and operations[state_pos] != 'I':
#        print "inserting" + str(i) +" " + str(position) + " " + str(skipped)+ " " + str(l_read) + " " + cigar +" " + str(l) + " " + insertion_string + "  " + operations[state_pos]

        ind = i+position-skipped - 1;
        if ind not in insertions:
            insertions[ind]= []
        insertions[ind].append(insertion_string)
    return 1

def drop_cash(cashed_sams, separate_sams):
    print ("dropping cashed lines...")
    for contig_info in cashed_sams:
        file_name = separate_sams[contig_info]
        file = open(file_name, "a");
        for line in cashed_sams[contig_info]:
            file.write(line);
        file.close();
        cashed_sams[contig_info] = []
    return;

def process_read_for_pairs(arr, l,m, pair_profile, symb_num, symb_pos, symb_state):
#    global profile
#    global insertions
    cigar = arr[5]
    aligned = arr[9];
    qual_aligned = arr[10]
    position = int(arr[3]) - 1
    map_q = int(arr[4]);
    mate = m;
    l_read = len(aligned);
    if '*' in cigar:
        return 0;
    if config["use_quality"]:
        mate *=  (1 - pow(10,map_q/-10))
    shift = 0;
    nums = []
    operations = []
    tms = "";
    aligned_length = 0;
    for i in range(0, len(cigar)):

        if cigar[i].isdigit():
             tms += cigar[i]
        else:
            nums.append(int(tms));
            operations.append(cigar[i]);
            if cigar[i]=='M':
                aligned_length += int(tms)
            tms = ''
#we do not need short reads aligned near gaps
    if aligned_length < min(l_read* 0.4, 40) and position > l_read/2 and l - position > l_read/2 and mate == 1:
        return 0;
    state_pos = 0;
    shift = 0;
    skipped = 0;
    deleted = 0;
    int_A = ord('A') - 1
    for i in range(0, l_read):
        if i + position - skipped >= l:
            break;

        if shift + nums[state_pos] <= i:
            shift += nums[state_pos]
            state_pos += 1
        if operations[state_pos] == 'M':
            if i +  position - skipped < l:
                t_mate = mate;
                if config["use_quality"]:
                    k = pow(10, (ord(qual_aligned[i - deleted]) - int_A ) /-10);
                    if qual_aligned[i - deleted] == 'B':
                        t_mate *= 0.2
                    else:
                        t_mate = t_mate * (1 - k/(k+1))
                symb_pos.append(i+position -skipped);
                symb_state.append(aligned[i - deleted])
                symb_num += 1;
        else:
            if  operations[state_pos] in ('S', 'I', 'H'):
                skipped += 1;
            elif operations[state_pos] == 'D':
                deleted += 1;
    return symb_num


def split_sam(filename, tmpdir):
    global total_contigs;
    inFile = open(filename)
    separate_sams ={}
    mult_aligned = {}
    cashed_sams = {}
    print("file "+ filename+" opened")
    read_num = 0;

    import subprocess
#    ulimit = subprocess.check_output("ulimit -n", shell=True)
#    print "ulimit :", ulimit
#    ulimit = int(ulimit)
    need_to_cashe = True;
#TODO: whether multiple aligned helps?
#    needed_ulimit = total_contigs * 2 + 20
#    if (ulimit < needed_ulimit):
#        print ("Limit for simultaniously opened file is too small. limit: " + str(ulimit) + "; needed: " + str(needed_ulimit))
#        print ("Increasing it will speedup this stage for a while")
#        print ("For most systems (if you are a sudoer) you can fix it by adding \"*  soft    nofile    "+ str(needed_ulimit + 20) + "\" to /etc/security/limits.conf")
#        need_to_cashe = True

    paired_read = []
    processed_reads = 0;
    max_cashed_lines = 1000000;
    for line in inFile:
        arr = line.split()
        processed_reads += 1;
        if (processed_reads % max_cashed_lines == 0 and need_to_cashe):
            print processed_reads
            drop_cash(cashed_sams , separate_sams);
        if len(arr) > 5:
            read_num += 1
            paired_read.append(line.strip())
            if read_num == 2:
                unique = {}
                all_contigs = {}
                for j in range(0, 2):
                    tags = paired_read[j].split()[11:]
                    parsed_tags = {}
                    unique_fl = paired_read[j].split()[2];
                    all_contigs[unique_fl] = 1;
                    AS = 0;
                    XS = -1000;
                    if paired_read[j].split()[5] == "*":
                        unique_fl = ''
                    else:
                        for tag in tags:
                            tr = tag.split(':')
                            tag_name = tr[0]
                            tag_val = tr[2];
                            if (tag_name == "X0" and int(tag_val) > 1):
                                unique_fl = '';
                            elif (tag_name == "AS"):
                                AS = tag_val
                            elif (tag_name == "XS"):
                                XS = tag_val
                    if unique_fl != '' and AS > XS:
                        unique[unique_fl] = 1

                for cont_name in all_contigs :
                    if cont_name in separate_sams:
                        for j in range(0,2):
                            if (not need_to_cashe):
                                separate_sams[cont_name].write(paired_read[j]+ '\n')
#                                if cont_name in unique:
#                                    separate_sams[cont_name].write(paired_read[j]+ '\n')
#                                else:
#                                    mult_aligned[cont_name].write(paired_read[j]+ '\n')
                            else:
                                cashed_sams[cont_name].append(paired_read[j] + '\n');

                read_num = 0;
                paired_read = []
#            if arr[2] in separate_sams:
#                separate_sams[arr[2]].write(line)

        else:
            contig = arr[1].split(':')
            if contig[0] == 'SN':
                samfilename = tmpdir + '/' +contig[1].split('_')[1] + '.pair.sam'
                multalignedfilename = tmpdir + '/' +contig[1].split('_')[1] + '.multiple.sam'
#               print contig[1] + " " + samfilename;
                if need_to_cashe:
                    separate_sams[contig[1]] = samfilename
                    cashed_sams[contig[1]] = [];
                else:
                    separate_sams[contig[1]] = open(samfilename, 'w')
                    mult_aligned[contig[1]] = open(multalignedfilename , 'w')
    if (need_to_cashe):
        drop_cash(cashed_sams , separate_sams);
        cashed_sams = None
    else:
        for file_name in separate_sams:
            separate_sams[file_name].close()




    return 0

def split_reads(filename):
    splitted_reads = []

    left = config["work_dir"]+filename.split('/')[-1].split('.')[0]+ "_1.fastq"
    right = config["work_dir"]+filename.split('/')[-1].split('.')[0]+ "_2.fastq"
    leftFile = open(left, "w")
    rightFile = open(right, "w")
    count = 0
    state = 0
    for line in open(filename, 'r'):
        if (state == 0):
            leftFile.write(line)
        else:
            rightFile.write(line)
        count += 1;
        if count == 4:
            count = 0
            state = 1 - state
    leftFile.close()
    rightFile.close()
    config["reads1"] = left
    config["reads2"] = right

def split_contigs(filename, tmpdir):
    global total_contigs;
    ref_seq = read_contigs(filename);
    for contig_desc in ref_seq:
        tfilename = tmpdir + '/' + contig_desc.split('_')[1] +'.fasta'
        total_contigs += 1;
        write_fasta([[contig_desc, ref_seq[contig_desc]]], tfilename)

def usage():
    print >> sys.stderr, 'Corrector. Simple postprocessing tool'
    print >> sys.stderr, 'Usage: python', sys.argv[0], '[options] -1 left_reads -2 right_reads -c contigs'
    print >> sys.stderr, 'Or: python', sys.argv[0], '[options] --12 mixed_reads -c contigs'
    print >> sys.stderr, 'Or: python', sys.argv[0], '[options] -s sam_file -c contigs'
    print >> sys.stderr, 'Options:'
    print >> sys.stderr, '-t/--threads  <int>   threads number'
    print >> sys.stderr, '-o/--output_dir   <dir_name>  directory to store results'
    print >> sys.stderr, '-m/--mate-weight  <int>   weight for paired reads aligned properly. By default, equal to single reads weight (=1)'
    print >> sys.stderr, '--bwa <path>   path to bwa tool. Required if bwa is not in PATH'
    print >> sys.stderr, '--bowtie2    <path>  path to bowtie2 tool. Can be used instead of bwa; is faster but provides a bit worse results'
    print >> sys.stderr, '  --use_quality use quality values as probabilities '
    print >> sys.stderr, '  --debug   save all intermediate files '
    print >> sys.stderr, '  --use_multiple_aligned  use paired reads with multiple alignment'
    print >> sys.stderr, '  --skip_masked   do not correct single \'N\', provided by assembler'
    print >> sys.stderr, '  --insert_size <int> estimation on insert size'

def run_aligner():
    global config

    #    (contigs_name, path, suf) = fileparse(config.contigs)
    if not "contigs" in config:
        print "NEED CONTIGS TO REFINE!!!"
        usage()
        exit()
    if not "reads1" in config or not "reads2" in config:
        if not "reads_mixed" in config:
            print "NEED READS TO REFINE!!!"
            usage()
            exit()
        else:
            split_reads(config["reads_mixed"])
    contigs_name = config["contigs"].split('/')[-1];
    work_dir = config['work_dir']
    os.system("cp " + config["contigs"] + " " + work_dir)
#    os.system("cp " + config["reads1"] + " " + work_dir)
#    os.system("cp " + config["reads2"] + " " + work_dir)
    contigs_name = work_dir + contigs_name
    reads_1 = work_dir + config["reads1"].split('/')[-1]
    reads_2 = work_dir + config["reads2"].split('/')[-1]
#    config["reads1"] = reads_1
#    config["reads2"] = reads_2
    config["sam_file"] = work_dir + "tmp.sam"
    config["contigs"] = contigs_name

    print ("config")
    if "bowtie2" in config:
        print("bowtie2 found, aligning")
        run_bowtie2()
    else:
        print("running bwa")
        run_bwa()

def run_bowtie2():
    global config;
    os.system(config["bowtie2"] + "-build " + config["contigs"] + " " + config["work_dir"] + "tmp > /dev/null")
    os.system(config["bowtie2"] + " -x" + config["work_dir"] + "tmp  -1 " + config["reads1"] + " -2 " + config["reads2"] + " -S " + config["sam_file"] + " -p " + str(config["t"])+ " --local  --non-deterministic")
def run_bwa():
# align with BWA
    global config;

    os.system(config["bwa"] + " index -a is " + config["contigs"] + " 2")
    os.system(config["bwa"] + " aln  "+ config["contigs"] +" " + config["reads1"] + " -t " + str(config["t"]) + "  -O 7 -E 2 -k 3 -n 0.08 -q 15 >"+config["work_dir"]+ "tmp1.sai" )
    os.system(config["bwa"] + " aln  "+ config["contigs"] +" " + config["reads2"] + " -t " + str(config["t"]) + " -O 7 -E 2 -k 3 -n 0.08 -q 15 >"+config["work_dir"]+ "tmp2.sai" )
    os.system(config["bwa"] + " sampe "+ config["contigs"] +" " + config["work_dir"]+ "tmp1.sai "+config["work_dir"]+ "tmp2.sai " + config["reads1"] + " " + config["reads2"] + ">"+config["work_dir"]+ "tmp.sam 2>"+config["work_dir"]+ "isize.txt")
    return 0


def parse_profile(args):
    global config

    long_options = "threads= sam_file= output_dir= bwa= contigs= mate_weight= splitted_dir= bowtie2= 12= insert_size= help debug use_quality use_multiple_aligned skip_masked".split()
    short_options = "1:2:o:s:S:c:t:m:q"
    options, contigs_fpaths = getopt.gnu_getopt(args, short_options, long_options)
    for opt, arg in options:
        if opt in ('-o', "--output-dir"):
            config["output_dirpath"] = os.path.abspath(arg)
            config["make_latest_symlink"] = False
        if opt in ('-c', "--contigs"):
            config["contigs"] = os.path.abspath(arg)
            if not os.path.exists(config["contigs"]):
                print "FILE WITH CONTIGS DOES NOT EXIST!"
                usage()
                exit(1)
        if opt in ('-1'):
            config["reads1"] = os.path.abspath(arg)
            if not os.path.exists(config["reads1"]):
                print "FILE WITH READS DOES NOT EXIST!"
                usage()
                exit(1)
        if opt in ('-2'):
            config["reads2"] = os.path.abspath(arg)
            if not os.path.exists(config["reads2"]):
                print "FILE WITH READS DOES NOT EXIST!"
                usage()
                exit(1)
        if opt in ('--12'):
            config["reads_mixed"] = os.path.abspath(arg)
            if not os.path.exists(config["reads12"]):
                print "FILE WITH READS DOES NOT EXIST!"
                usage()
                exit(1)
        if opt in ("--bwa"):
            config["bwa"] = os.path.abspath(arg)
        if opt in ('-t', "--threads"):
            config["t"] = int(arg)
        if opt in ('-m', "--mate_weight"):
            config["mate_weight"] = float(arg)
        if opt in ('-s', "--sam_file"):
            config["sam_file"] = os.path.abspath(arg)
        if opt in ('-S', "--splitted_dir"):
            config["splitted_dir"] = os.path.abspath(arg)
        if opt in ('-q', "--use_quality"):
            config["use_quality"]= 1;
        if opt in ("--bowtie2"):
            if arg != "bowtie2":
                arg = os.path.abspath(arg)
            config["bowtie2"]= arg;
        if opt in ("--debug"):
            config["debug"] = 1;
        if opt in ("--use_multiple_aligned"):
            config["use_multiple_aligned"] = 1;
        if opt in ("--skip_masked"):
            config["skip_masked"] = 1;
        if opt in ('--insert_size'):
            config["reads_mixed"] = int(arg)

    work_dir = config["output_dirpath"]+"/tmp/"
    config["work_dir"] = work_dir
    os.system ("mkdir -p " + work_dir)
    os.system("rm -rf " + work_dir + "/*")


def init_config():
    now = datetime.datetime.now()
    config["output_dirpath"] = "corrector.output." + now.strftime("%Y.%m.%d_%H.%M.%S")+"/";
    config["bwa"] = "bwa"
    config["t"] = int(4)
    config["mate_weight"] = float(1)
    config["use_quality"] = 0;
    config["debug"] = 0;
    config["use_multiple_aligned"] = 0;
    config["skip_masked"] = 0;
    config["insert_size"] = int(400)

def chouseLetters(first_node, second_node, prof, node, choused_letter, single_profile, interest, contig, logFile):
#    print first_node;
#    print second_node;
    logFile.write( "total factors number -- " + str(len(first_node)))
    if len(first_node) == 0:
        return
    current_nodes = [first_node[0], second_node[0]];
    active_current_nodes = [first_node[0], second_node[0]];
    non_zero_seq = [];
    active_non_zero_seq = [];
    non_zero_weight = []
    for s1 in ('A','C','G','T','N'):
        for s2 in ('A','C','G','T','N'):
            if prof[0][s1][s2] > 0:
                non_zero_seq.append(str(s1)+str(s2));
		non_zero_weight.append(prof[0][s1][s2])
                active_non_zero_seq.append(str(s1)+str(s2));
#                print non_zero_seq[len(non_zero_seq)-1]
    fact_num = len(first_node);
    last_processed_first_node = first_node[0] 
    for i in range (1, fact_num):
#        print "process factor " + str(i) + " of " + str(fact_num) + ": " + str(first_node[i]) + " --> " + str(second_node[i])
#	print non_zero_seq;
#	print non_zero_weight;
#	print current_nodes;
#	print active_non_zero_seq;
#	print active_current_nodes;
#	print "from " + str(first_node[i]) + " to " + str(second_node[i])
#	print prof[i]
 #       print len(non_zero_seq)
        ind1 = -1
	if last_processed_first_node != first_node[i]:
            while last_processed_first_node < first_node[i]:
#                print last_processed_first_node, " ", first_node[i], " ", active_current_nodes
 #reduce strings
                aind1 = active_current_nodes.index(last_processed_first_node)
                for j in range (0, len(active_non_zero_seq)):
#                    print aind1, " ", active_non_zero_seq[j], " -> ", active_non_zero_seq[j][:aind1], " + ", active_non_zero_seq[j][aind1+1:],  
                    active_non_zero_seq[j] = active_non_zero_seq[j][:aind1] + active_non_zero_seq[j][aind1+1:];
                for j in range (0, len(active_non_zero_seq)):
                    str1 = active_non_zero_seq[j];
                    for k in range (j+1, len(active_non_zero_seq)):
                        str2 = active_non_zero_seq[k];
                        if (str1 == str2):
                            if (non_zero_weight[j] < non_zero_weight[k]):
                                non_zero_weight[j] = 0
                                break
                            else:
                                non_zero_weight[k] = 0
                del active_current_nodes[aind1];    
                k = 0
                while k < len (non_zero_seq):
                    if (non_zero_weight[k] == 0):
                        del non_zero_weight[k]
                        del non_zero_seq[k]
                        del active_non_zero_seq[k]
                    else:
                        k += 1
                if len (active_current_nodes) == 0:
                    break
                last_processed_first_node = min (active_current_nodes)
        
        last_processed_first_node = first_node[i];
        if (first_node[i] in current_nodes):
            ind1 = current_nodes.index(first_node[i])
	else: 
            max_node = max(current_nodes)
#            if second_node[i] in current_nodes or :
            if first_node[i] < max_node:
                ind1 = len (current_nodes)
		k = len(non_zero_seq)
                current_nodes.append(first_node[i])
                active_current_nodes.append(first_node[i])
                possible_letters = [];
                for s1 in ('A','C','G','T','N'):
                    if single_profile[first_node[i]][s1] > 0:
                        possible_letters.append(s1)
                while k > 0:
                    for s1 in possible_letters:
                        non_zero_seq.append(non_zero_seq[0]+s1)
                        active_non_zero_seq.append(active_non_zero_seq[0]+s1)
                        non_zero_weight.append(non_zero_weight[0])
                    del non_zero_seq[0]
                    del active_non_zero_seq[0]
                    del non_zero_weight[0]
                    k -= 1
        if ind1 > -1: #current_nodes[0] = first_node[i]:
            ind = -1
            if second_node[i] in current_nodes:
                ind = current_nodes.index(second_node[i])
            if ind == -1:
                ind = len (current_nodes)
                current_nodes.append(second_node[i])
                active_current_nodes.append(second_node[i])
                possible_letters = [];
                for s1 in ('A','C','G','T','N'):
                    if single_profile[second_node[i]][s1] > 0:
                        possible_letters.append(s1)
		k = len(non_zero_seq)
                while k > 0:
                    for s1 in possible_letters:
                        non_zero_seq.append(non_zero_seq[0]+s1)
                        active_non_zero_seq.append(active_non_zero_seq[0]+s1)
                        non_zero_weight.append(non_zero_weight[0])
                    del non_zero_seq[0]
                    del active_non_zero_seq[0]
                    del non_zero_weight[0]
                    k -= 1
            k = 0
#	    print "ind1 =  ", ind1, "   ind = ", ind
            while k < len (non_zero_seq):
#                print non_zero_seq[k]
                non_zero_weight[k] *= prof[i][non_zero_seq[k][ind1]][non_zero_seq[k][ind]]
                if (non_zero_weight[k] == 0):
                    del non_zero_weight[k]
                    del non_zero_seq[k]
                    del active_non_zero_seq[k]
                else:
                    k += 1
#            print "non zero strings: " + str (k)
            if len(non_zero_weight) > 125:
                max_start_node = max(current_nodes)
#                print "seeking for factors that can reduce this"
                for r in range (i+1, fact_num):
#                    print "factor ", r,": ", first_node[r], " ->  ", second_node[r]
                    if first_node[r] in current_nodes and second_node[r] in current_nodes:
                        act_ind1 = current_nodes.index(first_node[r]);
                        act_ind2 = current_nodes.index(second_node[r]);
#                        print "factor ", r,": ", first_node[r], " ->  ", second_node[r]
#                        print "with ", prof[r] 
                        k = 0
                        while k < len (non_zero_seq):
                            if (prof[r][non_zero_seq[k][act_ind1]][non_zero_seq[k][act_ind2]] == 0):
                                del non_zero_weight[k]
                                del non_zero_seq[k]
                                del active_non_zero_seq[k]
                            else:
                                k += 1
                    elif max_start_node < first_node[r]:
                        break
#                print "reduced down to " + str(len (non_zero_seq))
                if len(non_zero_weight) > 5000:
                    while 0 < len (non_zero_seq):
                        del non_zero_weight[0]
                        del non_zero_seq[0]
                        del active_non_zero_seq[0]
                     
#            if len (non_zero_seq) == 0:
#                print "No pathes"
        else:
#            print "non zero pathes:"    
#            for j in range (0, len(non_zero_seq)):
#                print non_zero_seq[j] + " " + str(non_zero_weight[j])
            if len(non_zero_seq) > 0: 
                max_ind = 0
                for j in range (1, len(non_zero_seq)):
                    if (non_zero_weight[max_ind] < non_zero_weight[j]):
                        max_ind = j
#                allNs = 1
                allNs = 0
                for j in range (0, len(current_nodes)):
                    if j in interest and contig[j] != 'N':
                        allNs = 0
                        break
                if allNs == 0:
                    for j in range (0, len(current_nodes)):
                        node.append(current_nodes[j])
                        choused_letter.append(non_zero_seq[max_ind][j])
            current_nodes = [first_node[i], second_node[i]];
            active_current_nodes = [first_node[i], second_node[i]];
            non_zero_seq = [];
            non_zero_weight = []
            active_non_zero_seq = [];
            last_processed_first_node = first_node[i]
            for s1 in ('A','C','G','T','N'):
                for s2 in ('A','C','G','T','N'):
                    if prof[i][s1][s2] > 0:
                        non_zero_seq.append(str(s1)+str(s2));
                        non_zero_weight.append(prof[i][s1][s2])
                        active_non_zero_seq.append(str(s1)+str(s2));
#                        print non_zero_seq[len(non_zero_seq)-1]
#    print "non zero pathes:"    
#    for i in range (0, len(non_zero_seq)):
#        print non_zero_seq[i] + " " + str(non_zero_weight[i])
#    print "All done";
#    print non_zero_seq;
#    print non_zero_weight;
#    print current_nodes;
#    print active_non_zero_seq;
#    print active_current_nodes;

    if len(non_zero_seq) > 0: 
        max_ind = 0
        for j in range (1, len(non_zero_seq)):
            if (non_zero_weight[max_ind] < non_zero_weight[j]):
                max_ind = j
#       allNs = 1
        allNs = 0
        for j in range (0, len(current_nodes)):
            if j in interest and contig[j] != 'N':
                allNs = 0
                break
        if allNs == 0:
            for j in range (0, len(current_nodes)):
                node.append(current_nodes[j])
                choused_letter.append(non_zero_seq[max_ind][j])


def process_contig(files):
    samfilename = files[0]
    contig_file = files[1]
    if len(files) == 3:
        mult_aligned_filename = files[2]
    profile = []
    mult_profile = []
    insertions = {}
    mult_insertions = {}
    inserted = 0;
    replaced = 0;
    deleted = 0;
    pair_profile = {}


    fasta_contig = read_genome(contig_file);
#no spam about short contig processing
    if len(fasta_contig[1]) > 20000:
        print "processing long contig " + str(contig_file) + ", contig length:" + str(len(fasta_contig[1]));
    contig = fasta_contig[1].upper()
    #            profile = []
    total_reads = 0;
    indelled_reads = 0;
    #            print samfilename
    contig_name = samfilename.split('/')[-1].split('.')[0]
    refinedFileName = config["work_dir"] + contig_name + '.ref.fasta';
    logFileName =  config["work_dir"] + contig_name + '.stdout';
    logFile = open(logFileName, 'w')
    #    samFile = io.open( sys.argv[1], 'r');
    # accurate!
    cont_num = contig_file.split('/')[-1].split('.')[0];
    #    fasta_contig = read_genome(sys.argv[2]);
    stime = datetime.datetime.now();
    logFile.write(stime.strftime("%Y.%m.%d_%H.%M.%S") + ":  Start!\n");
    starttime = stime;



    l = len(contig)
    #            print l;
    #            print contig
    if config["use_multiple_aligned"]:
        mult_alignedFile = open(mult_aligned_filename, 'r')
        for line in mult_alignedFile:
            arr = line.split();
            if arr[2].split('_')[1] != cont_num:
                continue
            process_read(arr, l, 1, mult_profile, mult_insertions)

    rescontig = ""
    for i in range (0, l):
        profile.append( {} );
        mult_profile.append({});
        for j in ('A','C','G','T','N','I','D'):
            profile[i][j] = 0;
            mult_profile[i][j] = 0;
    #TODO: estimation on insert size, need to be replaced

    insert_size_est = config["insert_size"]
    samFile = open(samfilename, 'r');
    for line in samFile:
        arr = line.split();
        if arr[2].split('_')[1] != cont_num:
            continue
            #        print line;
#	print arr[0]

        cigar = arr[5]
        aligned = arr[9];
        position = int(arr[3]) - 1
        tags = arr[11:]
        parsed_tags = {}
        for tag in tags:
            parsed_tags[tag.split(':')[0]] = tag.split(':')[2]
        mate_el = arr[6];
        #Mate of non-end read in other contig
        #TODO: contig breaker/ fixer can be here
        if mate_el != '=' and mate_el != '*' and (position > config["insert_size"] and position < l - config["insert_size"] - 100 ):
            continue;
        #Mate not in this contig; another alignment of this read present
        if mate_el != '=' and ("XA" in parsed_tags or ("XS" in parsed_tags and "AS" in parsed_tags and parsed_tags["XS"] >= parsed_tags["AS"])):
#        and (("X0" in parsed_tags and parsed_tags["X0"] > 1)):

            continue;
        if mate_el == '=' and (int(arr[1]) & 8) == 0:
            mate = config["mate_weight"];
        else:
            mate = 1;
        indelled_reads += 1 - process_read(arr, l, mate, profile, insertions)
        total_reads += 1;
    ntime = datetime.datetime.now()
    stime = ntime - stime
    logFile.write(ntime.strftime("%Y.%m.%d_%H.%M.%S")+": File processed. ");
    logFile.write("elapsed time time: " + str(stime) + "\n");
    stime = ntime
    interest = set([])
    interest100 = set(range(0, l, 100))
    for i in range (0, l):
        alls = 0;
        for s1 in ('A','C','G','T','N'):
            alls += profile[i][s1];
	ini = 0;
#        print i," ", profile[i] 
        for s1 in ('A','C','G','T','N'):
            if (profile[i][s1] > 0.1 * alls) and (profile[i][s1] < 0.9 * alls) and (alls > 20):
                ini += 1;
        if ini > 1 or (contig[i] == 'N'):
            interest.add(i)
            interest100.add(i)
    read_name = "";
    prev_read_name = "";
    max_dist =  config["insert_size"];
    int_seq = [];
    int_nodes = [];
    int_seq_cnt = []; 
    logFile.write( str(contig_file)+": interesting positions - " + str(len(interest)) )
#    print str(contig_file)+": ", interest
    logFile.write( str(contig_file)+": working positions " + str(len(interest100)))
    for i in interest100:
        pair_profile[i] = {}
        for j in interest100:
            if i < j and j - i < max_dist:
                pair_profile[i][j] = {}
                for s1 in ('A','C','G','T','N'):
                    pair_profile[i][j][s1] = {}
                    for s2 in ('A','C','G','T','N'):
                        pair_profile[i][j][s1][s2] = 0;
    ntime = datetime.datetime.now()
    stime = ntime - stime
    logFile.write(ntime.strftime("%Y.%m.%d_%H.%M.%S")+":  Prepare pair profile. ");
    logFile.write("elapsed time time: " + str(stime) + "\n");
    stime = ntime
#    print "second go"
    samFile.seek(0)
    read_processed = 0
    for line in samFile:
#        print "second go +"
        arr = line.split();
        if arr[2].split('_')[1] != cont_num:
            continue
            #        print line;
        read_name = arr[0];
        cigar = arr[5]	
        aligned = arr[9];
        position = int(arr[3]) - 1
        tags = arr[11:]
        parsed_tags = {}
        for tag in tags:
            parsed_tags[tag.split(':')[0]] = tag.split(':')[2]
        mate_el = arr[6];
        #Mate of non-end read in other contig
        #TODO: contig breaker/ fixer can be here
#	print read_name
        if mate_el != '=' and mate_el != '*' and (position > insert_size_est and position < l - insert_size_est - 100 ):
            if read_processed == 1:
                for i in range(0, len (symb_pos)):
                    if symb_pos[i] in interest100:
                        for j in range(i+1, len (symb_pos)):
                            if symb_pos[j] in interest100:
                                if symb_pos[j] > symb_pos[i] and symb_pos[j] - symb_pos[i] < max_dist: 
                                    pair_profile[symb_pos[i]][symb_pos[j]][symb_state[i]][symb_state[j]] += 1;
                                elif symb_pos[j] < symb_pos[i] and symb_pos[i] - symb_pos[j] < max_dist:
                                    pair_profile[symb_pos[j]][symb_pos[i]][symb_state[j]][symb_state[i]] += 1;
            symb_pos = []
            symb_state = []
            read_processed = 0
            prev_read_name = read_name
            continue;
        #Mate not in this contig; another alignment of this read present
        if mate_el != '=' and ("XA" in parsed_tags or ("XS" in parsed_tags and "AS" in parsed_tags and parsed_tags["XS"] >= parsed_tags["AS"])):
#        and (("X0" in parsed_tags and parsed_tags["X0"] > 1)):
            if read_processed == 1:
                for i in range(0, len (symb_pos)):
                    if symb_pos[i] in interest100:
                        for j in range(i+1, len (symb_pos)):
                            if symb_pos[j] in interest100:
                                if symb_pos[j] > symb_pos[i] and symb_pos[j] - symb_pos[i] < max_dist: 
                                    pair_profile[symb_pos[i]][symb_pos[j]][symb_state[i]][symb_state[j]] += 1;
                                elif symb_pos[j] < symb_pos[i] and symb_pos[i] - symb_pos[j] < max_dist:
                                    pair_profile[symb_pos[j]][symb_pos[i]][symb_state[j]][symb_state[i]] += 1;
            symb_pos = []
            symb_state = []
            read_processed = 0
            prev_read_name = read_name
            continue;
        if mate_el == '=' and (int(arr[1]) & 8) == 0:
            mate = config["mate_weight"];
        else:
            mate = 1;
        if read_name == prev_read_name:
            symb_num = process_read_for_pairs(arr, l,mate, pair_profile, symb_num, symb_pos, symb_state)
            read_processed = 0
            for i in range(0, len (symb_pos)):
                if symb_pos[i] in interest100:
                    for j in range(i+1, len (symb_pos)):
                        if symb_pos[j] in interest100:
                            if symb_pos[j] > symb_pos[i] and symb_pos[j] - symb_pos[i] < max_dist: 
                                pair_profile[symb_pos[i]][symb_pos[j]][symb_state[i]][symb_state[j]] += 1;
                            elif symb_pos[j] < symb_pos[i] and symb_pos[i] - symb_pos[j] < max_dist:
                                pair_profile[symb_pos[j]][symb_pos[i]][symb_state[j]][symb_state[i]] += 1;
            symb_pos = []
            symb_state = []
        else:
            if read_processed == 1:
                for i in range(0, len (symb_pos)):
                    if symb_pos[i] in interest100:
                        for j in range(i+1, len (symb_pos)):
                            if symb_pos[j] in interest100:
                                if symb_pos[j] > symb_pos[i] and symb_pos[j] - symb_pos[i] < max_dist: 
                                    pair_profile[symb_pos[i]][symb_pos[j]][symb_state[i]][symb_state[j]] += 1;
                                elif symb_pos[j] < symb_pos[i] and symb_pos[i] - symb_pos[j] < max_dist:
                                    pair_profile[symb_pos[j]][symb_pos[i]][symb_state[j]][symb_state[i]] += 1;
            symb_num = 0
            symb_state = []
            symb_pos = []
            process_read_for_pairs(arr, l,mate, pair_profile, symb_num, symb_pos, symb_state)
            read_processed = 1
#        total_reads += 1;
        prev_read_name = read_name
    

    ntime = datetime.datetime.now()
    stime = ntime - stime
    logFile.write(ntime.strftime("%Y.%m.%d_%H.%M.%S")+": File processed second time. ");
    logFile.write("elapsed time time: " + str(stime) + "\n");
    stime = ntime

    first_node = [];
    second_node = [];
    prof = [];
    my_interest_range = list(interest100)
    my_interest_range.sort()
    for i in my_interest_range:
        for j in my_interest_range:
            if j > i and j - i < max_dist:
                alls = 0;
                all1 = {};
                all2 = {};
                for s1 in ('A','C','G','T','N'):
                    for s2 in ('A','C','G','T','N'):
                        alls += pair_profile[i][j][s1][s2];
                for s1 in ('A','C','G','T','N'):
                    for s2 in ('A','C','G','T','N'):
                        if pair_profile[i][j][s1][s2] < alls / 1000:
                            pair_profile[i][j][s1][s2] = 0;
                fun1 = 1
                fun2 = 1
                if (i in interest) and alls > 20:
                    fun1 = 2
                if ((j) in interest) and alls > 20:
                    fun2 = 2
#		print i, " ", j, " ", pair_profile[i][j]
#		print fun1, " ", fun2
                
                if fun1 * fun2 > 1 and alls > 0:
                    first_node.append(i);
		    second_node.append(j);
                    prof.append(pair_profile[i][j])
#                print str(i) + " -- "+ str(i+j);
#                for s1 in ('A','C','G','T','N'):
#                    for s2 in ('A','C','G','T','N'):
#                        print s1+ "->"+ s2 +": "+ str(pair_profile[i][j][s1][s2]);
    ntime = datetime.datetime.now()
    stime = ntime - stime
    logFile.write(ntime.strftime("%Y.%m.%d_%H.%M.%S")+": Factors prepared. ");
    logFile.write("elapsed time time: " + str(stime) + "\n");
    stime = ntime
    node = [];
    choused_letter = [];
    chouseLetters(first_node, second_node, prof, node, choused_letter, profile, interest, contig, logFile)
#    print "checked positions:"
#    print node 
#    print choused_letter
    ntime = datetime.datetime.now()
    stime = ntime - stime
    logFile.write(ntime.strftime("%Y.%m.%d_%H.%M.%S")+": Letters choused. ");
    logFile.write("elapsed time time: " + str(stime) + "\n");
    stime = ntime

    for i in range (0, l):
        tj = contig[i]
        skip = 0;
        if (tj == 'N' and config["skip_masked"] and not i in node):
            skip = 1;
        tmp = ''
        mate_weight = config["mate_weight"]
#cycle on count is usefull for insertions only
        for count in range(0,2):
            for j in ('A','C','G','T','N', 'I', 'D'):
#first condition trivial,
# second - for insertions we have both the base after insertion and 'I' (but want to have more than one 'I' to insert),
# third - to avoid issues with multiple alignment OK, but few uniquely discordant erroneous reads making to "correct"
# position
                if (profile[i][tj] < profile[i][j] or \
                    (j == 'I' and profile[i][tj] < 1.5 * profile[i][j] and profile[i][j] > mate_weight)) and \
                    mult_profile[i][tj] < profile[i][j] * 10:

                    tj = j
                    #                rescontig[i] = j
            if tj != 'I' and i in node:
#                print "Letter ", choused_letter[node.index(i)], " forced by potentials, ", tj, " sugested for position ", i, " by profile while ",  contig[i], " present"
                tj = choused_letter[node.index(i)]
                if tj != contig[i] :
                    logFile.write ("forced changing " + contig[i] + " to " + tj + " on position " + str(i+1) +'\n')

            if tj != contig[i] :
                if tj != 'I' and skip:
                    rescontig += 'N'
                    break;
                if tj =='I' or tj == 'D' :
                    logFile.write ("there was in-del \n")
                else:
                    replaced += 1
                logFile.write (str(profile[i]))
                logFile.write("changing " + contig[i] + " to " + tj + " on position " + str(i+1) +'\n')

            if tj in ('A','C','T','G','N'):
                rescontig += tj
                break;
            elif tj == 'D':
                logFile.write( "skipping deletion"+ " on position " + str(i+1) +'\n')
                deleted += 1;
                break;
            elif tj == 'I':
                tmp = vote_insertions(i,insertions);

                profile[i]['I'] = 0;
        if tmp != '':
            rescontig += tmp;
            inserted += len (tmp)
    res_fasta = [[]]
    res_fasta[0].append(fasta_contig[0]);
    res_fasta[0].append(rescontig)
    write_fasta(res_fasta, refinedFileName)
    ntime = datetime.datetime.now()
    stime = ntime - stime
    logFile.write(ntime.strftime("%Y.%m.%d_%H.%M.%S") + ": All done. ");
    logFile.write("elapsed time time: " + str(stime) + "\n");
    stime = ntime - starttime
    logFile.write("Time spended: " + str(stime) + "\n");

    logFile.write("Finished processing "+ str(contig_file) + ". Used " + str(total_reads) + " reads.\n")
    logFile.write("replaced: " + str(replaced) + " deleted: "+ str(deleted) +" inserted: " + str(inserted) +'\n')
#    return inserted, replaced
    return;

def main(args):
    paired_read = []
    if len(args) < 1:
        usage()
        exit(0)

    deleted = 0;
    init_config()
    parse_profile(args)
    inserted = 0;
    replaced = 0;
    print(config)
    if "splitted_dir" not in config:
#        print "no splitted dir, looking for sam file"
        if "sam_file" not in config:
            print "no sam file, running aligner"
            run_aligner()
        else:
            print "sam file found"
            os.system("cp -p "+ config["sam_file"] +" " + config["work_dir"]+"tmp.sam")
            config["sam_file"] = config["work_dir"]+"tmp.sam"
    #    now = datetime.datetime.now()
    #    res_directory = "corrector.output." + now.strftime("%Y.%m.%d_%H.%M.%S")+"/";
        split_contigs(config["contigs"],config["work_dir"])
        print("contigs splitted, starting splitting .sam file");
        split_sam(config["sam_file"], config["work_dir"])
        print(".sam file splitted")
    else:
        print "splitted tmp dir found, starting correcting"
        os.system("cp "+ config["splitted_dir"] +"/* " + config["work_dir"])
    #    return 0
#    if not os.path.exists(res_directory):
#        os.makedirs(res_directory)
#    refinedFileName = res_directory + sys.argv[2].split('/')[-1].split('.')[0] + '.ref.fasta';

    filelist = [os.path.abspath(os.path.join(config["work_dir"], i)) for i in os.listdir(config["work_dir"]) if os.path.isfile(os.path.join(config["work_dir"], i))]
    pairs = []
    for contig_file in filelist:
        f_name = contig_file.split('/')[-1];
        f_arr = f_name.split('.');
        if len(f_arr) == 2 and f_arr[1][0:2] == "fa" and os.path.exists(os.path.join("/".join(contig_file.split('/')[:-1]), f_arr[0]+".pair.sam")):
            samfilename = os.path.join("/".join(contig_file.split('/')[:-1]), f_arr[0]+".pair.sam");
            mult_aligned_filename = os.path.join("/".join(contig_file.split('/')[:-1]), f_arr[0]+".multiple.sam");
            tmp = []
            tmp.append(samfilename)
            tmp.append(contig_file)
            if (config["use_multiple_aligned"]):
                tmp.append(mult_aligned_filename)
            tmp.append(os.path.getsize(contig_file))
            pairs.append(tmp)
    pairs.sort(key=lambda x: x[-1], reverse=True)
    Parallel(n_jobs=config["t"])(delayed(process_contig)(pair)for pair in pairs)
#        inserted += loc_ins;
#        replaced += loc_rep;
    replaced = 0;
    deleted = 0;
    inserted = 0;
    cat_line = "cat "+ config["work_dir"] + "/*.ref.fasta > "+ config["work_dir"] + "../corrected_contigs.fasta"
    print cat_line
    os.system(cat_line);
    filelist = [os.path.abspath(os.path.join(config["work_dir"], i)) for i in os.listdir(config["work_dir"]) if os.path.isfile(os.path.join(config["work_dir"], i))]
    for stdout_file in filelist:
        if stdout_file.split('.')[-1] == 'stdout':
            stdoutFile = open(stdout_file, 'r')

            for line in stdoutFile:
                arr = line.split()
                if arr[0] == "replaced:":
                    replaced += int(arr[1])
                    deleted += int(arr[3])
                    inserted += int(arr[5])
        elif config["debug"] == 0:
            os.system("rm " + stdout_file)
    print ("TOTAL - replaced: " + str(replaced) + " deleted: "+ str(deleted) +" inserted: " + str(inserted))


#    print "TOTAL replaced: "+ str(replaced) + " inserted: "+ str(inserted) + " deleted: " + str(deleted);


if __name__ == '__main__':
    main(sys.argv[1:])
