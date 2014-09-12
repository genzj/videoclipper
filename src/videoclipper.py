import lya
import sys
import subprocess
import os
import json
from io import BytesIO
from datetime import timedelta
from math import ceil

def prepare_output_dir(proj):
    proj.outdir = os.path.abspath(os.path.join(
                 proj.output.dir,
                 proj.title))
    outdir = proj.outdir
    try:
        os.makedirs(outdir)
    except Exception as err:
        print(err)

    if not os.path.isdir(outdir):
        print('%s is not a dir'%(outdir,))
    elif not os.access(outdir, os.F_OK):
        print('fail to create dir %s'%(outdir,))
    elif not os.access(outdir, os.R_OK | os.W_OK):
        print('dir %s is not accessible'%(outdir,))

def test_video(proj):
    video = proj.video
    probep = subprocess.Popen(
                 [ffprobe, '-i', video, '-show_error', '-of', 'json'],
                 stdout = subprocess.PIPE, stderr = subprocess.DEVNULL
            )
    ans = probep.communicate()[0]
    try:
        ans = json.loads(ans.decode(sys.getfilesystemencoding()))
        if 'error' in ans:
            print('cannot open video file: %s' % (ans['error']['string'],))
            return False
    except Exception as error:
        print(error)
    return True

def parse_timestamp(s):
    ''' convert a timestamp alike string or float to timedelta object

    Understand string like:
        HH:MM:SS.milliseconds
        MM:SS.milliseconds
        SS.milliseconds
    The milliseconds part along with the dot(.) are optional

    Float and any other types could be converted to strings of
    above format by builtin str() function are also acceptable.
    '''
    s = str(s)
    hour, min, sec, milli = 0, 0, 0, 0

    if '.' in s:
        s, milli = s.split('.', 1)
        milli = '0.' + milli

    if s.count(':') < 1: sec = s
    elif s.count(':') < 2: min, sec = s.split(':')
    elif s.count(':') < 3: hour, min, sec = s.split(':')
    else: raise Exception('"%s" is not a valid time string'%(s,))

    try:
        milli = float(milli) * 1000
        hour, min, sec, milli = map(int, (hour, min, sec, milli))
    except:
        raise Exception('"%s" is not a valid time string'%(s,))

    return timedelta(hours=hour, minutes=min, seconds=sec, milliseconds=milli)

def get_offset_duration(clip):
    s, e = map(parse_timestamp, (clip['start'], clip['end']))
    if s >= e:
        raise Exception('clip %(title)s: start time %(start)s of should be earlier than end time %(end)s' % clip)

    return clip['start'], str(ceil((e-s).total_seconds()))



def clip(proj, clip, overwrite=True):
    buf = BytesIO()
    output = os.path.join(proj.outdir, '%(idx)02d-%(title)s-%(speaker)s'%clip)
    output = '.'.join([output, proj.output.format])
    overwriteopt = '-y' if overwrite else '-n'
    offset, duration = get_offset_duration(clip)
    print('outfile:', output)
    cmd = [ffmpeg, '-ss', offset, '-i', proj.video, '-c', 'copy',
           '-nostdin', overwriteopt, '-t', duration, output ]
    ffmpegp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        out = ffmpegp.stdout.read(1)
        buf.write(out)
        if out in (b'\r', b'\n'):
            sys.stdout.write(buf.getvalue().decode().strip('\x00'))
            buf.truncate(0)

        if ffmpegp.returncode is None:
            if ffmpegp.poll() is not None: break
        else:
            break;


ffmpeg = r'D:\bin\ffmpeg\bin\ffmpeg.exe'
ffprobe = r'D:\bin\ffmpeg\bin\ffprobe.exe'

encoding = None
def main():
    fp = os.path.abspath(sys.argv[1])
    os.chdir(os.path.dirname(fp))

    with open(fp, 'r', encoding=encoding) as f:
        proj = lya.AttrDict.from_yaml(f)
        proj.video = os.path.abspath(proj.video)
        proj.config = fp

    prepare_output_dir(proj)
    if test_video(proj):
        idx = 1
        for section in proj.sections:
            section['idx'] = idx
            clip(proj, section)
            idx += 1

if __name__ == '__main__':
    main()


