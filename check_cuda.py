import torch, sys
print('python', sys.version)
print('torch', torch.__version__)
try:
    cuda_ok = torch.cuda.is_available()
    print('cuda_available', cuda_ok)
    if cuda_ok:
        print('device_count', torch.cuda.device_count())
        for i in range(torch.cuda.device_count()):
            print(i, torch.cuda.get_device_name(i))
except Exception as e:
    print('error checking cuda:', e)
