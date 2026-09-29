import os

from rest_framework import serializers

from .extract import (
    ALLOWED_EXTENSIONS,
    basename,
    extension_of,
    extract_text,
    read_upload,
)
from .models import KnowledgeDocument

MAX_UPLOAD_BYTES = 20 * 1024 * 1024


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    soubor = serializers.FileField(write_only=True, required=False)
    has_text = serializers.SerializerMethodField()
    nahral_jmeno = serializers.SerializerMethodField()
    download_path = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'nazev', 'popis', 'aktivni',
            'original_filename', 'velikost', 'has_text',
            'nahral', 'nahral_jmeno', 'download_path',
            'vytvoreno', 'upraveno', 'soubor',
        ]
        read_only_fields = [
            'original_filename', 'velikost', 'nahral',
            'vytvoreno', 'upraveno',
        ]

    def get_has_text(self, obj):
        return bool((obj.extracted_text or '').strip())

    def get_nahral_jmeno(self, obj):
        user = obj.nahral
        if not user:
            return ''
        name = f'{user.jmeno} {user.prijmeni}'.strip()
        return name or user.uzivatelske_jmeno

    def get_download_path(self, obj):
        return f'/api/knowledge/documents/{obj.id}/download/'

    def validate(self, attrs):
        uploaded = attrs.get('soubor')
        if self.instance is None and uploaded is None:
            raise serializers.ValidationError({'soubor': 'Nahrajte soubor.'})
        if uploaded is not None:
            ext = extension_of(uploaded.name)
            if ext not in ALLOWED_EXTENSIONS:
                raise serializers.ValidationError({
                    'soubor': 'Povolené typy: PDF, DOCX, TXT a obrázky (bez OCR).',
                })
            size = getattr(uploaded, 'size', None) or 0
            if size > MAX_UPLOAD_BYTES:
                raise serializers.ValidationError({'soubor': 'Soubor je větší než 20 MB.'})
        nazev = attrs.get('nazev')
        if nazev is not None:
            nazev = nazev.strip()
            attrs['nazev'] = nazev
        if self.instance is None and 'aktivni' not in self.initial_data:
            attrs['aktivni'] = True
        if not nazev:
            if uploaded is not None and self.instance is None:
                stem = os.path.splitext(basename(uploaded.name))[0].strip()
                attrs['nazev'] = (stem or 'Dokument')[:255]
            elif self.instance is None:
                raise serializers.ValidationError({'nazev': 'Vyplňte název.'})
        return attrs

    def _apply_upload(self, validated_data):
        uploaded = validated_data.get('soubor')
        if uploaded is None:
            return None
        data = read_upload(uploaded)
        validated_data['original_filename'] = basename(uploaded.name)[:255]
        validated_data['velikost'] = len(data)
        validated_data['extracted_text'] = extract_text(data, uploaded.name)
        return self.instance.soubor.name if self.instance and self.instance.soubor else None

    def create(self, validated_data):
        self._apply_upload(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        previous = self._apply_upload(validated_data)
        instance = super().update(instance, validated_data)
        if previous and instance.soubor and previous != instance.soubor.name:
            instance.soubor.storage.delete(previous)
        return instance
