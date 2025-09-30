from pathlib import Path
f = Path(__file__).resolve().parents[1] / 'data' / 'assist09' / 'train.txt'
if not f.exists():
    print('Missing:', f)
    raise SystemExit(1)
with open(f, 'r', encoding='utf-8') as fh:
    lines = [l.strip() for l in fh if l.strip()!='']
student_count = 0
problems = set()
skills = set()
total_interactions = 0
warnings = []
if len(lines) % 4 != 0:
    warnings.append(f"File {f} line count {len(lines)} not multiple of 4")
for i in range(0, len(lines), 4):
    if i+3 >= len(lines):
        warnings.append(f"Truncated block starting at line {i+1}")
        break
    seq_len_line = lines[i]
    try:
        seq_len = int(seq_len_line)
    except Exception:
        warnings.append(f"Non-integer seq_len '{seq_len_line}' at block starting line {i+1}")
        continue
    qline = lines[i+1]
    skillline = lines[i+2]
    resp_line = lines[i+3]
    qids = [int(x) for x in qline.split(',') if x!='']
    skids = [int(x) for x in skillline.split(',') if x!='']
    resps = [x for x in resp_line.split(',') if x!='']
    if not (len(qids) == len(skids) == len(resps) == seq_len):
        warnings.append(f"Length mismatch in block starting line {i+1}: seq_len={seq_len}, qids={len(qids)}, skills={len(skids)}, resps={len(resps)}")
    student_count += 1
    problems.update(qids)
    skills.update(skids)
    total_interactions += len(qids)
print('File:', str(f))
print('Unique students (blocks):', student_count)
print('Unique problems (question ids):', len(problems))
print('Unique skills (skill/pid ids):', len(skills))
print('Total interactions (sum lengths):', total_interactions)
if warnings:
    print('\nWarnings:')
    for w in warnings[:50]:
        print('-', w)
    if len(warnings) > 50:
        print('... and', len(warnings)-50, 'more warnings')
