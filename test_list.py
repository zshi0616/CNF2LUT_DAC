import numpy as np 
import os 
import copy
import glob
import time 
import argparse
from wrapper import *

CASE_DIR = '/Users/zhengyuanshi/studio/dataset/sat_2023'
# CASE_DIR = '/Users/zhengyuanshi/studio/dataset/LEC/all_case_cnf/'
CASE_LIST = [
    # 'a26', 'a28', 'b30',    # SAT
    # 'ac36', 'a3', 'ad6',    # UNSAT
    # '00f4aca773e5675f35263dcd46b15bde-vmpc_28.shuffled-as.sat05-1957', 
    # '7b4622a3ab523264378a560199de47ed-ER_400_20_4.apx_1_DC-ST', 
    # '578b5e6a2f0b295168cb6c5420810a72-php18-mixed-35percent-blocked', 
    # '10196804504080e7107809a2e5b3bfcc-ContextModel_output_6_5_6.bul_.dimacs',
    '8ade10da9731ce31d103c1687ff40a3d-brent_63_0.15' 
]

BL_TIME_LISTS = [
    [0, 1.82], 
    [0, 49], 
    [0, 53], 
    [0, 268], 
    [0, 447]
]

if __name__ == '__main__':
    tot_bl_time = 0
    tot_c2l_solvetime = 0
    tot_c2l_transtime = 0
    tot_c2lsam_solvetime = 0
    tot_c2lsam_transtime = 0
    
    if len(CASE_LIST) == 0:
        for case_path in glob.glob(os.path.join(CASE_DIR, '*.cnf')):
            case = os.path.basename(case_path)[:-4]
            CASE_LIST.append(case)
    
    for case in CASE_LIST:
        print('[INFO] Case: {:}'.format(case))
        cnf_path = os.path.join(CASE_DIR, '{}.cnf'.format(case) )
        if not os.path.exists(cnf_path):
            print('[WARNING] {:} not exists'.format(cnf_path))
            continue
        if os.stat(cnf_path).st_size > 10 * 1024 * 1024:
            print('[WARNING] {:} too large'.format(cnf_path))
            continue
        
        ####################################################################
        # Baseline: CNF -> SAT
        ####################################################################
        # bl_res, _, bl_timelist = baseline_solve(cnf_path)
        bl_res = -1
        bl_timelist = BL_TIME_LISTS.pop(0)
        
        bl_time = bl_timelist[1]
        if bl_res == -1:
            print('[WARNING] Baseline Timeout')
        print('[INFO] Result: {:}'.format(bl_res))
        print('Baseline Time: {:.2f}s'.format(bl_timelist[1]))
        tot_bl_time += bl_time
        # bl_res = -1
        # bl_time = 1
        
        ####################################################################
        # C2L: CNF -> LUT -> CNF -> SAT
        ####################################################################
        # c2l_res, _, c2l_timelist = cnf2lut_solve(cnf_path, verify=False)
        c2l_res = -1
        c2l_timelist = [1000, 1000]
        
        c2l_time = c2l_timelist[0] + c2l_timelist[1]
        if c2l_res == -1:
            print('[WARNING] c2l Timeout')
        print('[INFO] Result: {:}'.format(c2l_res))
        if bl_res != -1 and c2l_res != -1:
            assert bl_res == c2l_res
        print('[INFO] C2L Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
            c2l_timelist[0], c2l_timelist[1], c2l_time, 
            (bl_time - c2l_time) / bl_time * 100
        ))
        tot_c2l_solvetime += c2l_timelist[1]
        tot_c2l_transtime += c2l_timelist[0]
        
        # ####################################################################
        # # C2LSAM: CNF -> LUT -> SAM -> CNF -> SAT
        # ####################################################################
        c2lsam_res, _, c2lsam_timelist = cnf2lut_samsat_solve(cnf_path)
        c2lsam_time = c2lsam_timelist[0] + c2lsam_timelist[1]
        if c2lsam_res == -1:
            print('[WARNING] c2lsam Timeout')
        print('[INFO] Result: {:}'.format(c2lsam_res))
        if bl_res != -1 and c2lsam_res != -1:
            assert c2lsam_res == bl_res
        print('[INFO] C2LSAM Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
            c2lsam_timelist[0], c2lsam_timelist[1], c2lsam_time, 
            (bl_time - c2lsam_time) / bl_time * 100
        ))
        tot_c2lsam_solvetime += c2lsam_timelist[1]
        tot_c2lsam_transtime += c2lsam_timelist[0]
        
        # ####################################################################
        # # C2A: CNF -> AIG -> CNF -> SAT
        # ####################################################################
        # c2a_res, _, c2a_timelist = cnf2aig_solve(cnf_path)
        # c2a_time = c2a_timelist[0] + c2a_timelist[1]
        # if c2a_res == -1:
        #     print('[WARNING] c2a Timeout')
        # if bl_res != -1 and c2a_res != -1:
        #     assert c2a_res == bl_res
        # print('[INFO] C2A Trans. {:.2f}s, Solve: {:.2f}s, Tot: {:.2f}s | Red.: {:.2f}%'.format(
        #     c2a_timelist[0], c2a_timelist[1], c2a_time, 
        #     (bl_time - c2a_time) / bl_time * 100
        # ))
        
        
        print()
    
    print()
    print('=' * 10 + ' PASS ' + '=' * 10)
    print('Total Baseline Time: {:.2f}s'.format(tot_bl_time))
    print('C2L Total Trans. Time: {:.2f}s, Solve Time: {:.2f}s'.format(
        tot_c2l_transtime, tot_c2l_solvetime
    ))
    print('C2L Total Time: {:.2f}s'.format(tot_c2l_transtime + tot_c2l_solvetime))
    print('C2LSAM Total Trans. Time: {:.2f}s, Solve Time: {:.2f}s'.format(
        tot_c2lsam_transtime, tot_c2lsam_solvetime
    ))
    print('C2LSAM Total Time: {:.2f}s'.format(tot_c2lsam_transtime + tot_c2lsam_solvetime))