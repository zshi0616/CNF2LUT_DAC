import os 
import glob 
from utils.logger import Logger
import utils.cnf_utils as cnf_utils
import datetime
import time

from main import cnf2lut
from main import main as cnf2lut_bench
from utils.utils import run_command
import utils.lut_utils as lut_utils

CNF_DIR = '/Users/zhengyuanshi/studio/dataset/sat_2023'
output_dir = '/Users/zhengyuanshi/studio/dataset/sat_2023_cnf2lut'
output_bench_dir = '/Users/zhengyuanshi/studio/dataset/sat_2023_lutbench'

CASE_LIST = []

if __name__ == '__main__':
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(output_bench_dir):
        os.makedirs(output_bench_dir)
    
    if len(CASE_LIST) == 0:
        for case in glob.glob(os.path.expanduser(CNF_DIR) + '/*.cnf'):
            CASE_LIST.append(os.path.basename(case).replace('.cnf', ''))
    
    for case in CASE_LIST:
        case_path = os.path.join(CNF_DIR, '{}.cnf'.format(case))
        if not os.path.exists(case_path):
            print('[ERROR] Case not found: {}'.format(case_path))
            continue
        if os.path.getsize(case_path) > 1024 * 1024 * 100:
            continue
        
        print(f'Processing {case_path}...')
        
        cnf, no_var = cnf_utils.read_cnf(case_path)
        cnf = cnf_utils.sort_cnf(cnf)
        start_time = time.time()
        bench_x_data, bench_fanin_list, po_list, const_1_list = cnf2lut(cnf, no_var)
        trans_time = time.time() - start_time
        
        # Parse Bench
        for idx in range(len(bench_x_data)):
            bench_x_data[idx] = ['N{:}'.format(idx), bench_x_data[idx][2]]
        bench_cnf = lut_utils.convert_cnf(bench_x_data, bench_fanin_list, const_1_list=const_1_list)
        no_vars = len(bench_x_data)
        
        # Save 
        converted_cnf_path = os.path.join(output_dir, '{}.cnf'.format(case))
        cnf_utils.save_cnf(bench_cnf, no_vars, converted_cnf_path)
        
        # Output 
        print('# Vars: {:}, # Clauses: {:}'.format(no_vars, len(bench_cnf)))
        print('Trans Time: {:.2f}s'.format(trans_time))
        print('Converted to: {}'.format(converted_cnf_path))
        print()