import yaml
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
    cmd = [conf.tools.ffprobe, '-i', video, '-hide_banner', '-show_error', '-of', 'json']

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

def clip(proj, clip):
    buf = BytesIO()
    output = os.path.join(proj.outdir, '%(idx)02d-%(title)s-%(speaker)s'%clip)
    output = '.'.join([output, proj.output.format])
    overwriteopt = '-y' if conf.clip.overwrite else '-n'
    offset, duration = get_offset_duration(clip)
    cmd = [conf.tools.ffmpeg, '-ss', offset, '-i', proj.video, '-c', 'copy',
           '-nostdin', overwriteopt, '-t', duration, output ]
    logger.info('exporting clip %d to %s', clip['idx'], output)
    logger.debug('export cmd "%s"', ' '.join(cmd))
    ffmpegp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while True:
        out = ffmpegp.stdout.read(1)
        if out in (b'\r', b'\n'):
            if len(buf.getvalue()) > 0:
                ffmpeglogger.info(buf.getvalue().decode().strip('\x00'))
                buf.truncate(0)
        else:
            buf.write(out)

        if ffmpegp.returncode is None:
            if ffmpegp.poll() is not None: break
        else:
            break;

class ClipConfig(lya.AttrDict):
    def dump(self, stream):
        yaml.representer.SafeRepresenter.add_representer(
            ClipConfig, yaml.representer.SafeRepresenter.represent_dict )
        super().dump(stream)

    def __str__(self):
        buf = BytesIO()
        self.dump(buf)
        return buf.getvalue().decode('utf-8').strip('\x00')

    @staticmethod
    def default_config():
        apppath = get_app_path()
        conf = ClipConfig()

        # section 'tools' in which ffmpeg binary pathes
        # are specified
        conf.tools = lya.AttrDict()
        conf.tools.ffmpeg = os.path.join(apppath, 'bin', 'ffmpeg.exe')
        conf.tools.ffprobe = os.path.join(apppath, 'bin', 'ffprobe.exe')

        # section 'debug' in which debug levels of individual
        # modules are specified
        conf.debug = lya.AttrDict()
        conf.debug.clipper = 'info'
        conf.debug.ffmpeg = 'warning'
        conf.debug.ffprobe = 'warning'

        # section 'clip' defines settings used in section exporting
        conf.clip = lya.AttrDict()
        conf.clip.overwrite = True
        conf.clip.encoding = None

        return conf

def main():
    fp = os.path.abspath(sys.argv[1])
    os.chdir(os.path.dirname(fp))

    with open(fp, 'r', encoding=conf.clip.encoding) as f:
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

def get_app_path(appfile=None):
    appfile = appfile if appfile else sys.argv[0]
    apppath = os.path.dirname(appfile)
    apppath = '.' if not apppath else apppath
    oldpath = os.path.abspath(os.curdir)
    os.chdir(apppath)
    apppath = os.path.abspath(os.curdir)
    os.chdir(oldpath)
    return os.path.normcase(apppath)

def load_config(filename = 'settings.yaml', create_if_not_exist = True):
    conffile = os.path.join(get_app_path(), filename)
    conf = ClipConfig.default_config()
    if os.access(conffile, os.F_OK):
        logger.info('try loading configuration from %s', conffile)
        try:
            conf.update_yaml(conffile)
        except Exception as err:
            logger.critical('cannot load configuration file', exc_info=err)
            sys.exit(2)

    elif create_if_not_exist:
        try:
            with open(conffile, 'wb') as outf:
                conf.dump(outf)
        except Exception as err:
            logger.warn('cannot create default configuration file', exc_info=err)

    logger.setLevel(log.getLevelByName(conf.debug.clipper))
    ffmpeglogger.setLevel(log.getLevelByName(conf.debug.ffmpeg))
    ffprobelogger.setLevel(log.getLevelByName(conf.debug.ffprobe))
    logger.debug("settings loaded:\n%s", conf)
    return conf


if __name__ == '__main__':
    global conf
    logger.setLevel(log.INFO)
    ffmpeglogger.setLevel(log.INFO)
    ffprobelogger.setLevel(log.INFO)
    conf = load_config()
    try:
        main()
    except Exception as err:
        logger.critical('error "%s" happen during handling, aboring...', err, exc_info=err)
        sys.exit(1)


