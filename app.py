import os
import re
import time
from flask import Flask, request, render_template, send_file, after_this_request
from pytube import YouTube
from moviepy.editor import VideoFileClip

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['MAX_FILE_AGE'] = 300  # 5 دقائق قبل حذف الملفات

# إنشاء مجلد التنزيلات إذا لم يكن موجوداً
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

def clean_filename(name):
    """تنظيف اسم الملف من الأحرف غير الآمنة"""
    return re.sub(r'[\\/*?:"<>|]', '', name)

@app.route('/')
def home():
    """عرض الصفحة الرئيسية"""
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    """الحصول على معلومات الفيديو"""
    url = request.form['url']
    
    try:
        yt = YouTube(url)
        video_info = {
            'title': yt.title,
            'duration': time.strftime('%H:%M:%S', time.gmtime(yt.length)),
            'thumbnail': yt.thumbnail_url,
            'channel': yt.author,
            'formats': []
        }
        
        # جمع التنسيقات المتاحة
        streams = yt.streams.filter(progressive=True, file_extension='mp4')
        for stream in streams:
            video_info['formats'].append({
                'itag': stream.itag,
                'resolution': stream.resolution,
                'filesize': f"{round(stream.filesize / (1024 * 1024), 1)} MB"
            })
        
        return video_info
    
    except Exception as e:
        return {'error': str(e)}, 400

@app.route('/download', methods=['POST'])
def download_video():
    """تنزيل الفيديو"""
    url = request.form['url']
    itag = request.form['itag']
    format_type = request.form['format']
    
    try:
        yt = YouTube(url)
        
        # تنظيف اسم الملف
        filename = clean_filename(yt.title)
        
        if format_type == 'mp3':
            # تنزيل الصوت
            stream = yt.streams.get_audio_only()
            file_extension = 'mp3'
            temp_path = stream.download(output_path=app.config['DOWNLOAD_FOLDER'], filename=filename)
            
            # تحويل إلى MP3
            video_clip = VideoFileClip(temp_path)
            output_path = os.path.splitext(temp_path)[0] + '.mp3'
            video_clip.audio.write_audiofile(output_path)
            video_clip.close()
            os.remove(temp_path)
        else:
            # تنزيل الفيديو
            stream = yt.streams.get_by_itag(int(itag))
            file_extension = 'mp4'
            output_path = stream.download(output_path=app.config['DOWNLOAD_FOLDER'], filename=filename)
        
        # إعداد إرسال الملف مع حذفه بعد التنزيل
        @after_this_request
        def remove_file(response):
            try:
                os.remove(output_path)
            except Exception as error:
                app.logger.error("خطأ في حذف الملف", error)
            return response
        
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"{filename}.{file_extension}"
        )
    
    except Exception as e:
        return {'error': str(e)}, 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)