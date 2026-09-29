import zipfile
from datetime import date
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from knowledge.extract import extract_text
from knowledge.models import KnowledgeDocument
from users.models import WebUser


def _pdf(text: str) -> bytes:
    safe = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream = f'BT /F1 12 Tf 72 72 Td ({safe}) Tj ET\n'.encode('latin-1')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
        b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'endstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    out = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f'{index} 0 obj\n'.encode())
        out.extend(obj)
        out.extend(b'\nendobj\n')
    xref = len(out)
    out.extend(f'xref\n0 {len(objects) + 1}\n'.encode())
    out.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        out.extend(f'{offset:010d} 00000 n \n'.encode())
    out.extend(
        f'trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    )
    return bytes(out)


def _docx(text: str) -> bytes:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>'
    )
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('word/document.xml', xml)
    return buffer.getvalue()


@override_settings(MEDIA_ROOT='/tmp/mobilmajak-knowledge-test-media')
class KnowledgeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = WebUser.objects.create(
            id=8821,
            uzivatelske_jmeno='kb_admin',
            jmeno='Admin',
            prijmeni='Kb',
            role='ADMIN',
            heslo='x',
        )
        self.seller = WebUser.objects.create(
            id=8822,
            uzivatelske_jmeno='kb_seller',
            jmeno='Prodejce',
            prijmeni='Kb',
            role='PRODEJCE',
            heslo='x',
        )

    def _upload(self, name, content, content_type, filename=None):
        self.client.force_authenticate(user=self.admin)
        uploaded = SimpleUploadedFile(filename or name, content, content_type=content_type)
        return self.client.post('/api/knowledge/documents/', {
            'nazev': name,
            'popis': 'popis',
            'soubor': uploaded,
        }, format='multipart')

    def test_anonymous_cannot_list(self):
        response = self.client.get('/api/knowledge/documents/')
        self.assertIn(response.status_code, (401, 403))

    def test_seller_can_list_but_not_upload_or_delete(self):
        created = self._upload('Navod', 'Reklamace postup.'.encode(), 'text/plain', 'navod.txt')
        self.assertEqual(created.status_code, 201, created.data)
        doc_id = created.data['id']
        self.assertIn('Reklamace postup', KnowledgeDocument.objects.get(pk=doc_id).extracted_text)

        self.client.force_authenticate(user=self.seller)
        listed = self.client.get('/api/knowledge/documents/')
        doc = KnowledgeDocument.objects.get()
        self.assertTrue(doc.aktivni)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)

        denied = self.client.post('/api/knowledge/documents/', {
            'nazev': 'X',
            'soubor': SimpleUploadedFile('a.txt', b'ahoj', content_type='text/plain'),
        }, format='multipart')
        self.assertEqual(denied.status_code, 403)

        removed = self.client.delete(f'/api/knowledge/documents/{doc_id}/')
        self.assertEqual(removed.status_code, 403)

        downloaded = self.client.get(f'/api/knowledge/documents/{doc_id}/download/')
        self.assertEqual(downloaded.status_code, 200)
        self.assertIn(b'Reklamace postup', b''.join(downloaded.streaming_content))

    def test_pdf_docx_and_image_extraction(self):
        pdf = self._upload('Pdf', _pdf('Reklamace z pdf'), 'application/pdf', 'navod.pdf')
        self.assertEqual(pdf.status_code, 201, pdf.data)
        self.assertIn('Reklamace', KnowledgeDocument.objects.get(pk=pdf.data['id']).extracted_text)

        docx = self._upload('Docx', _docx('Vymena displeje docx'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'navod.docx')
        self.assertEqual(docx.status_code, 201, docx.data)
        self.assertIn('displeje', KnowledgeDocument.objects.get(pk=docx.data['id']).extracted_text)

        image = self._upload('Foto', b'\x89PNG\r\n\x1a\nfake', 'image/png', 'foto.png')
        self.assertEqual(image.status_code, 201, image.data)
        self.assertEqual(KnowledgeDocument.objects.get(pk=image.data['id']).extracted_text, '')
        self.assertFalse(image.data['has_text'])

    def test_extract_helpers(self):
        self.assertIn('Reklamace', extract_text(_pdf('Reklamace z pdf'), 'a.pdf'))
        self.assertIn('displej', extract_text(_docx('vymena displej'), 'a.docx'))
        self.assertEqual(extract_text(b'\x89PNG', 'a.png'), '')

    def test_ask_returns_excerpt_or_empty(self):
        self._upload('Reklamace', 'Reklamace se resi s dokladem do 14 dnu.'.encode(), 'text/plain', 'rekl.txt')
        self._upload('Doba', 'Otevírací doba prodejny je do 18 hodin.'.encode(), 'text/plain', 'doba.txt')

        self.client.force_authenticate(user=self.seller)
        hit = self.client.post('/api/knowledge/ask/', {'question': 'reklamace doklad'}, format='json')
        self.assertEqual(hit.status_code, 200)
        self.assertGreaterEqual(len(hit.data['sources']), 1)
        self.assertIn('answer', hit.data)
        self.assertIn('Reklamace', hit.data['sources'][0]['title'])
        self.assertTrue(hit.data['sources'][0]['download_path'].endswith('/download/'))
        self.assertNotIn('Doba', hit.data['answer'])

        folded = self.client.post('/api/knowledge/ask/', {'question': 'oteviraci doba'}, format='json')
        self.assertEqual(folded.status_code, 200)
        self.assertEqual(folded.data['sources'][0]['title'], 'Doba')

        miss = self.client.post('/api/knowledge/ask/', {'question': 'xyzqwerty nikde'}, format='json')
        self.assertEqual(miss.status_code, 200)
        self.assertEqual(miss.data['sources'], [])
        self.assertIn('nic', miss.data['answer'].lower())

        empty = self.client.post('/api/knowledge/ask/', {'question': '   '}, format='json')
        self.assertEqual(empty.status_code, 400)

        anon = APIClient().post('/api/knowledge/ask/', {'question': 'reklamace'}, format='json')
        self.assertIn(anon.status_code, (401, 403))

    def test_inactive_hidden_from_seller_and_search(self):
        created = self._upload('Skryte', 'tajny postup reklamace'.encode(), 'text/plain', 'tajne.txt')
        doc_id = created.data['id']
        patched = self.client.patch(f'/api/knowledge/documents/{doc_id}/', {'aktivni': False}, format='json')
        self.assertEqual(patched.status_code, 200)

        self.client.force_authenticate(user=self.seller)
        listed = self.client.get('/api/knowledge/documents/')
        self.assertEqual(listed.data, [])
        asked = self.client.post('/api/knowledge/ask/', {'question': 'tajny postup'}, format='json')
        self.assertEqual(asked.data['sources'], [])
