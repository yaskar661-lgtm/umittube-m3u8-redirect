from flask import Flask, redirect, abort
import requests
import urllib3
import re
import time

# SSL uyarılarını gizle (verify=false kullandığımız için log kirliliğini önler)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Önbellek (Sürekli mywire.org adresine yük bindirmemek için)
CACHE = {}
CACHE_DURATION = 120  # 2 dakika cache

PLAYLIST_URL = "https://ytube-wars.mywire.org/noutube/playlist.m3u"

def get_stream_url_from_m3u(channel_key):
    try:
        # verify=false ile SSL sertifika hatalarını aşıyoruz
        response = requests.get(PLAYLIST_URL, verify=False, timeout=10)
        if response.status_code != 200:
            return None
            
        m3u_content = response.text
        
        # Basit bir M3U parse mantığı: 
        # Kanal adına veya key'e göre ilgili .m3u8 linkini satırlardan çekiyoruz
        lines = m3u_content.splitlines()
        for i, line in enumerate(lines):
            if channel_key in line and i + 1 < len(lines):
                # Bir sonraki satır genellikle gerçek akış linkidir
                next_line = lines[i + 1].strip()
                if next_line.startswith("http"):
                    return next_line
                    
        # Eğer özel bir kanal aranmıyorsa listedeki ilk http linkini alabilirsin (alternatif)
        for line in lines:
            if line.startswith("http"):
                return line.strip()
                
    except Exception as e:
        print(f"M3U Okuma Hatası: {e}")
    
    return None

@app.route('/stream/<channel_key>')
def redirect_from_m3u(channel_key):
    current_time = time.time()
    
    # 1. Önbellek kontrolü
    if channel_key in CACHE and (current_time - CACHE[channel_key]['time'] < CACHE_DURATION):
        return redirect(CACHE[channel_key]['url'], code=302)
        
    # 2. mywire.org üzerindeki M3U listesinden güncel linki bul
    stream_url = get_stream_url_from_m3u(channel_key)
    
    if stream_url:
        CACHE[channel_key] = {'url': stream_url, 'time': current_time}
        return redirect(stream_url, code=302)
    else:
        return abort(404, description="M3U listesinde bu kanal bulunamadı veya link çekilemedi.")

@app.route('/restart')
def restart_cache():
    global CACHE
    CACHE.clear()  # Tüm önbelleği sıfırlar, böylece sonraki istekler güncel linkleri doğrudan çeker.
    return jsonify({
        "status": "success",
        "message": "Önbellek başarıyla temizlendi. Sonraki istekler güncel M3U listesini yeniden çekecektir."
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
