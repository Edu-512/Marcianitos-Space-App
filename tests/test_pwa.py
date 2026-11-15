"""PWA contract checks: python -m unittest discover -s tests."""
import json
import unittest
from html.parser import HTMLParser
from PIL import Image
from utils.pwa import PWA_DIR, app_shell, pwa_routes

class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head = False
        self.tags = []
    def handle_starttag(self, tag, attrs):
        if tag == 'head': self.in_head = True
        if self.in_head: self.tags.append((tag, dict(attrs)))
    def handle_endtag(self, tag):
        if tag == 'head': self.in_head = False

class PwaContracts(unittest.TestCase):
    def test_real_head_preserves_frontend_and_links_manifest_once(self):
        parser = HeadParser()
        parser.feed(app_shell())
        manifests = [a['href'] for t,a in parser.tags if t=='link' and a.get('rel')=='manifest']
        self.assertEqual(manifests, ['./manifest.webmanifest'])
        scripts = [a for t,a in parser.tags if t=='script']
        self.assertTrue(any(a.get('type')=='module' for a in scripts))
        self.assertTrue(any(a.get('src')=='./pwa/register.js' for a in scripts))

    def test_manifest_and_png_dimensions(self):
        manifest = json.loads((PWA_DIR/'manifest.webmanifest').read_text(encoding='utf-8'))
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['start_url'], manifest['scope'])
        self.assertEqual(manifest['id'], manifest['scope'])
        sizes = set()
        for icon in manifest['icons']:
            with Image.open(PWA_DIR.parent/icon['src']) as image:
                self.assertEqual(icon['sizes'], f'{image.width}x{image.height}')
                self.assertEqual(image.format, 'PNG')
                sizes.add(image.size)
        self.assertTrue({(192,192),(512,512)} <= sizes)
        self.assertTrue(any(i['purpose']=='maskable' for i in manifest['icons']))
        with Image.open(PWA_DIR/'icons/apple-touch-icon.png') as image:
            self.assertEqual(image.size,(180,180))

    def test_worker_route_is_at_root(self):
        paths={r.path for r in pwa_routes()}
        self.assertTrue({'/','/manifest.webmanifest','/service-worker.js','/pwa'} <= paths)

if __name__=='__main__': unittest.main()
