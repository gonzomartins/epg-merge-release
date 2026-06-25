#!/usr/bin/env python3
import requests
import gzip
import os
import shutil
import subprocess
from datetime import datetime
from lxml import etree

EPG_URL_1 = os.environ["EPG_URL_1"]
EPG_URL_2 = os.environ["EPG_URL_2"]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def download_gz(url, ziel, name):
    log(f"Lade {name}...")
    r = requests.get(url, headers=HEADERS, stream=True, timeout=60, allow_redirects=True)
    r.raise_for_status()
    with open(ziel, 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    log(f"{name} OK ({os.path.getsize(ziel)/1024:.1f} KB)")

def entpacke_gz(gz_pfad):
    xml_pfad = gz_pfad.replace('.gz', '')
    with gzip.open(gz_pfad, 'rb') as f_in, open(xml_pfad, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    return xml_pfad

def merge_epg(xml1, xml2, ausgabe):
    log("Merge EPG...")
    root1 = etree.parse(xml1).getroot()
    root2 = etree.parse(xml2).getroot()
    for el in root2:
        root1.append(el)
    log(f"Kanaele: {len(root1.findall('channel'))} | Programme: {len(root1.findall('programme'))}")
    etree.ElementTree(root1).write(ausgabe, encoding='utf-8', xml_declaration=True)
    log("Merge OK!")

def komprimiere_gz(xml_pfad, gz_pfad):
    log("Komprimiere...")
    with open(xml_pfad, 'rb') as f_in, gzip.open(gz_pfad, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
    log(f"Komprimiert ({os.path.getsize(gz_pfad)/1024:.1f} KB)")

def main():
    print("=" * 55)
    log("EPG Job gestartet")
    gz1 = "/tmp/epg1.xml.gz"
    gz2 = "/tmp/epg2.xml.gz"
    xml1 = "/tmp/epg1.xml"
    xml2 = "/tmp/epg2.xml"
    merged_xml = "/tmp/epg_merged.xml"
    merged_gz = "epg_merged.xml.gz"
    
    try:
        download_gz(EPG_URL_1, gz1, "EPG 1")
        download_gz(EPG_URL_2, gz2, "EPG 2")
        log("Entpacke...")
        entpacke_gz(gz1)
        entpacke_gz(gz2)
        merge_epg(xml1, xml2, merged_xml)
        komprimiere_gz(merged_xml, merged_gz)
        
        # Git Upload Prozess
        log("Lade Datei ins Repository hoch...")
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        
        # Sicherstellen, dass wir auf dem richtigen Branch sind und aktuellen Stand haben
        subprocess.run(["git", "checkout", "-B", "main"], check=True)
        subprocess.run(["git", "pull", "origin", "main", "--rebase"], check=True)
        
        subprocess.run(["git", "add", "epg_merged.xml.gz"], check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if "epg_merged.xml.gz" in status.stdout:
            subprocess.run(["git", "commit", "-m", "Automatisches Update der EPG Datei"], check=True)
            
            # Authentifizierung über den GITHUB_TOKEN
            remote_url = f"https://x-access-token:{os.environ['GITHUB_TOKEN']}@github.com/{os.environ['GITHUB_REPOSITORY']}.git"
            subprocess.run(["git", "push", remote_url, "main"], check=True)
            log("FERTIG: Datei erfolgreich gepusht!")
        else:
            log("Keine Änderungen an der Datei – kein Push nötig.")
            
    except Exception as e:
        log(f"Fehler bei der Ausführung: {e}")
        raise e

if __name__ == "__main__":
    main()
