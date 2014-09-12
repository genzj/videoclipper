import lya
import sys
import subprocess
import os
import json
import log
from io import BytesIO
from datetime import timedelta
from math import ceil

logger = log.getChild('clipper')
ffmpeglogger = log.getChild('ffmpeg')
ffprobelogger = log.getChild('ffprobe')

def prepare_output_dir(proj):
    proj.outdir = os.path.abspath(os.path.join(
                 proj.output.dir,
                 proj.title))
    outdir = proj.outdir
    try:
        logger.info('preparing output folder %s', outdir)
        os.makedirs(outdir)
    except Exception as err:
        logger.debug('makedirs returns error %s', err)

    if not os.path.isdir(outdir):
        raise Exception('%s is not a dir'%(outdir,))
    elif not os.access(outdir, os.F_OK):
        raise Exception('fail to create dir %s'%(outdir,))
    elif not os.access(outdir, os.R_OK | os.W_OK):
        raise Exception('dir %s is not accessible'%(outdir,))

def test_video(proj):
    video = proj.video
    cmd = [ffprobe, '-i', video, '-hide_banner', '-show_error', '-of', 'json']

    logger.info('testing video file %s', video)
    logger.debug('testing with command "%s"', ' '.join(cmd))
    probep = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

    ans, err = probep.communicate()
    ffprobelogger.info('meta data: \n%s', err.decode())

    ans = json.loads(ans.decode(sys.getfilesystemencoding()))
    ffprobelogger.info('probe answers: %s', ans)

    if 'error' in ans:
        raise Exception('cannot open video file: (%(code)s) %(string)s' % ans['error'])
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
    logger.debug('parse timestamp %s %s', type(s), s)
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
        raise Exception('clip %(title)s: start time %(start)s should be earlier than end time %(end)s' % clip)
    duration = ceil((e-s).total_seconds())

    logger.debug('clip "%s" starts at %s ends at %s duration %d', clip['title'], clip['start'], clip['end'], duration)
    return clip['start'], str(duration)

def clip(proj, clip, overwrite=True):
    buf = BytesIO()
    output = os.path.join(proj.outdir, '%(idx)02d-%(title)s-%(speaker)s'%clip)
    output = '.'.join([output, proj.output.format])
    overwriteopt = '-y' if overwrite else '-n'
    offset, duration = get_offset_duration(clip)
    cmd = [ffmpeg, '-ss', offset, '-i', proj.video, '-c', 'copy',
           '-nostdin', overwriteopt, '-t', duration, output ]
    logger.info('exporting clip %d to %s', clip['idx'], output)
    logger.debug('export cmd "%s"', ' '.join(cmd))
    ffmpegp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        out = ffmpegp.stdout.read(1)
        if out in (b'\r', b'\n'):
            if len(buf.getvalue()) > 0:
                ffmpeglogger.debug(buf.getvalue().decode().strip('\x00'))
                buf.truncate(0)
        else:
            buf.write(out)

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
    logger.info('all clips have been exported.')

if __name__ == '__main__':
    logger.setLevel(log.INFO)
    ffmpeglogger.setLevel(log.INFO)
    try:
        main()
    except Exception as err:
        logger.critical('error "%s" happen during handling, aboring...', err, exc_info=err)


