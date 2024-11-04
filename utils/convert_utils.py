from itertools import combinations
import utils.cnf_utils as cnf_utils
from utils.simulator import dec2list, list2hex

def divide_long_clauses(cnf, no_var, max_length=4):
    res_cnf = []
    res_no_var = no_var
    for clause in cnf:
        if len(clause) < max_length:
            res_cnf.append(clause)
        else:
            # divide clause based on resolution rules 
            while len(clause) > max_length:
                new_var = res_no_var + 1
                res_cnf.append(clause[:max_length-1] + [new_var])
                res_no_var += 1
                clause = [-new_var] + clause[max_length-1:]
            res_cnf.append(clause)
    return res_cnf, res_no_var

def get_var_comb_map(cnf, max_length=5):
    var_comb_map = {}
    for clause_idx, clause in enumerate(cnf):
        var_comb = []
        for var in clause:
            var_comb.append(abs(var))
        var_comb = tuple(sorted(var_comb))
        if var_comb not in var_comb_map:
            var_comb_map[var_comb] = [clause_idx]
        else:
            var_comb_map[var_comb].append(clause_idx)
    
    # Find sub var_comb
    for var_comb in var_comb_map.keys():
        if len(var_comb) > max_length:
            continue
        for sub_var_len in range(1, len(var_comb)):
            sub_var_comb_list = list(combinations(var_comb, sub_var_len))
            for sub_var_comb in sub_var_comb_list:
                if sub_var_comb in var_comb_map:
                    var_comb_map[var_comb] += var_comb_map[sub_var_comb]
    
    # Sort by the number of clauses
    var_comb_map = {k: v for k, v in sorted(var_comb_map.items(), key=lambda item: len(item[1]), reverse=True)}
    
    # Var2Varcomb
    var2varcomb_map = {}
    for var_comb in var_comb_map.keys():
        for var in var_comb:
            if var not in var2varcomb_map:
                var2varcomb_map[var] = [var_comb]
            else:
                var2varcomb_map[var].append(var_comb)
                
    return var_comb_map, var2varcomb_map

def subcnf_simulation(clauses, var_list, fanout_var):
    truth_table = []
    no_vars = len(var_list)
    for pattern in range(int(pow(2, no_vars))):
        bin_asg = dec2list(pattern, no_vars)
        asg = []
        for idx in range(len(bin_asg)):
            if bin_asg[idx] == 0:
                asg.append(-1 * (var_list[idx]))
            else:
                asg.append(var_list[idx])
        p_eval = cnf_utils.evalute_cnf(clauses, asg + [fanout_var])
        f_eval = cnf_utils.evalute_cnf(clauses, asg + [-fanout_var])
        if p_eval == 0 and f_eval == 0:
            truth_table.append(-1)
        elif p_eval == 0 and f_eval == 1:
            truth_table.append(0)
        elif p_eval == 1 and f_eval == 0:
            truth_table.append(1)
        elif p_eval == 1 and f_eval == 1:
            truth_table.append(2)
    
    return truth_table

def select_cnf(cnf, clause_visited, fanout_idx, var_comb_map, var2varcomb_map, max_fanin=6):
    fanout_var = fanout_idx + 1
    assert fanout_var > 0, 'fanout_idx must be positive'
    if fanout_var not in var2varcomb_map:
        return [], [], []
    var_comb_list = var2varcomb_map[fanout_var]
    # Sort var_comb_list by the number of variables
    var_comb_list = sorted(var_comb_list, key=lambda x: -len(x))
    res_var_comb = []
    res_clauses = []
    res_clauses_index = []
    res_tt = []
    
    # first-fit for bin packing problem 
    for var_comb in var_comb_list:
        var_comb_wo_fanout = list(var_comb)
        var_comb_wo_fanout.remove(fanout_var)
        tmp_var_comb = list(set(res_var_comb + var_comb_wo_fanout))
        if len(tmp_var_comb) < max_fanin:
            for clause_idx in var_comb_map[var_comb]:
                if clause_visited[clause_idx] == 1:
                    continue
                res_var_comb = tmp_var_comb
                res_clauses.append(cnf[clause_idx])
                res_clauses_index.append(clause_idx)
        
    # Simulation 
    if len(res_clauses) == 0:
        # This fanout_var should be PI 
        return [], [], []
    if len(res_var_comb) == 0:
        # This fanout_var should be Const
        assert len(res_clauses) == 1
        assert len(res_clauses[0]) == 1
        assert abs(res_clauses[0][0]) == abs(fanout_var)
        if res_clauses[0][0] > 0:
            return [], res_clauses_index, [1]
        else:
            return [], res_clauses_index, [-1]
        
    res_tt = subcnf_simulation(res_clauses, res_var_comb, fanout_var)
    res_clauses_index = list(set(res_clauses_index))
    
    return res_var_comb, res_clauses_index, res_tt
 
def create_lut(lut_tt, lut_fanin_list):
    no_fanin = len(lut_fanin_list)
    lut_len = int(pow(2, no_fanin)) // 4
    # c = !a+b ==> c = 0xD (a, b)
    ordered_lut_fanin = lut_fanin_list[::-1]
    tt_hex = list2hex(lut_tt[::-1], lut_len)
    return tt_hex, ordered_lut_fanin

def traverse_graph(no_vars, x_data, visited, fanin_list, fanout_list, extra_pi, extra_po, po_list, gate_to_index):
    # BFS 
    q = []
    for start_node in po_list:
        q.append(start_node)
    while len(q) > 0:
        node = q.pop(0)
        for k, fanin_node in enumerate(fanin_list[node]):
            if 0 <= fanin_node < no_vars:
                if not visited[node][k]:
                    visited[node][k] = True
                    q.append(fanin_node)
                else:
                    # Add PI 
                    deloop_pi = len(x_data)
                    x_data.append([deloop_pi, gate_to_index['PI'], ''])
                    fanin_list.append([])
                    fanout_list.append([])
                    fanout_list[deloop_pi].append(node)
                    for fanin_k in range(len(fanin_list[node])):
                        if fanin_list[node][fanin_k] == fanin_node:
                            fanin_list[node][fanin_k] = deloop_pi
                    
                    # Add XNOR LUT 
                    deloop_xnor = len(x_data)
                    x_data.append([deloop_xnor, gate_to_index['LUT'], '9'])
                    fanin_list.append([fanin_node, deloop_pi])
                    fanout_list.append([])
                    for fanout_k in range(len(fanout_list[fanin_node])):
                        if fanout_list[fanin_node][fanout_k] == node:
                            fanout_list[fanin_node][fanout_k] = deloop_xnor
                    fanout_list[deloop_pi].append(deloop_xnor)
                    extra_po.append(deloop_xnor)

def add_extra_or(x_data, fanin_list, fanout_list, or_list, gate_to_index):
    k = 0
    while k < len(or_list):
        extra_or_idx = len(x_data)
        for p in [4, 3, 2, 1]:
            if k + p < len(or_list):
                no_tt_len = int(pow(2, p-1))
                x_data.append([extra_or_idx, gate_to_index['LUT'], 'f'*(no_tt_len-1)+'e'])
                fanin_list.append([])
                for i in range(p + 1):
                    fanin_list[-1].append(or_list[k + i])
                fanout_list.append([])
                or_list.append(extra_or_idx)
                k += (p + 1)
                break
        else:
            # print('[INFO] PO: %d' % or_list[k])
            break
    return x_data, fanin_list, fanout_list, or_list[k]

