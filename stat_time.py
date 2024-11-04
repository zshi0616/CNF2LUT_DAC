import os 
import re

log_path = '1028.log'
TO = 1000

if __name__ == '__main__':
    f = open(log_path, "r")
    lines = f.readlines()
    f.close()
    
    # 正则表达式解析日志
    case_pattern = re.compile(r"\[INFO\] Case: (.+)")
    baseline_pattern = re.compile(r"Baseline Time: ([\d.]+)s")
    c2l_pattern = re.compile(r"C2L .* Tot: ([\d.]+)s")
    c2lsam_pattern = re.compile(r"C2LSAM .* Tot: ([\d.]+)s")
    timeout_pattern = re.compile(r"\[WARNING\] c2l Timeout")

    # 存储结果的列表
    cases = []
    current_case = None

    # 逐行解析日志
    for line in lines:
        case_match = case_pattern.search(line)
        baseline_match = baseline_pattern.search(line)
        c2l_match = c2l_pattern.search(line)
        c2lsam_match = c2lsam_pattern.search(line)
        timeout_match = timeout_pattern.search(line)

        if case_match:
            # 开始新case
            current_case = {
                "name": case_match.group(1),
                "baseline_time": TO + 1,
                "c2l_time": TO + 1,
                "c2lsam_time": TO + 1
            }
            cases.append(current_case)

        elif baseline_match and current_case:
            # 记录Baseline时间
            current_case["baseline_time"] = float(baseline_match.group(1))

        elif c2l_match and current_case:
            # 记录C2L总时间
            current_case["c2l_time"] = float(c2l_match.group(1))

        elif c2lsam_match and current_case:
            # 记录C2LSAM总时间
            current_case["c2lsam_time"] = float(c2lsam_match.group(1))

        elif timeout_match and current_case:
            # Timeout情况下的时间设置为1000s
            current_case["c2l_time"] = 1000.0

    # 打印解析结果
    # for case in cases:
    #     print(f"Case: {case['name']}")
    #     print(f"  Baseline Time: {case['baseline_time']}s")
    #     print(f"  C2L Total Time: {case['c2l_time']}s")
    #     print(f"  C2LSAM Total Time: {case['c2lsam_time']}s\n")
    
    for case in cases:
        if case['baseline_time'] > TO:
            case['baseline_time'] = TO
        if case['c2l_time'] > TO:
            case['c2l_time'] = TO
        if case['c2lsam_time'] > TO:
            case['c2lsam_time'] = TO

    no_succ = 0
    succ_index = []
    for case_k, case in enumerate(cases):
        if case['baseline_time'] < 100:
            continue
        if case['baseline_time'] > (TO-10):
            continue
        print(f"{case['name']} {case['c2lsam_time']}")
        no_succ += 1
        succ_index.append(case_k)
    # Write Case Name 
    f = open('selected_case.txt', 'w')
    for k, case_k in enumerate(succ_index):
        if k < len(succ_index) - 1:
            f.write('\'{}\', '.format(cases[case_k]['name']))
        else:
            f.write('\'{}\''.format(cases[case_k]['name']))
    print()

    # Write Baseline Time
    
    
            
    
    bl_times = []
    c2l_times = []
    c2lsam_times = []
    for case_k in succ_index:
        bl_times.append(cases[case_k]['baseline_time'])
        c2l_times.append(cases[case_k]['c2l_time'])
        c2lsam_times.append(cases[case_k]['c2lsam_time'])
    
    print('#{}'.format(no_succ))
    print("Baseline Time: {:.2f}".format(sum(bl_times)))
    print('C2L Time: {:.2f} ({:.2f}%)'.format(sum(c2l_times), (sum(bl_times) - sum(c2l_times)) / sum(bl_times) * 100))
    print('C2LSAM Time: {:.2f} ({:.2f}%)'.format(sum(c2lsam_times), (sum(bl_times) - sum(c2lsam_times)) / sum(bl_times) * 100))