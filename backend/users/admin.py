from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django import forms
from .models import WebUser, ProfilovyObrazek

class WebUserAdminForm(forms.ModelForm):
    """Formulář pro správu uživatelů s možností změny hesla"""
    nove_heslo = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        help_text="Zadejte nové heslo (ponechte prázdné pro zachování současného)"
    )
    
    class Meta:
        model = WebUser
        fields = '__all__'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Pokud bylo zadáno nové heslo, hashujeme ho
        nove_heslo = self.cleaned_data.get('nove_heslo')
        if nove_heslo:
            user.heslo = make_password(nove_heslo)
        
        if commit:
            user.save()
        return user

@admin.register(WebUser)
class WebUserAdmin(admin.ModelAdmin):
    form = WebUserAdminForm
    
    list_display = ('id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'role', 'aktivni', 'datum_vytvoreni')
    list_filter = ('role', 'aktivni', 'datum_vytvoreni')
    search_fields = ('id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'email')
    readonly_fields = ('datum_vytvoreni',)
    
    fieldsets = (
        ('Základní informace', {
            'fields': ('id', 'uzivatelske_jmeno', 'jmeno', 'prijmeni', 'nove_heslo', 'role', 'aktivni')
        }),
        ('Osobní údaje', {
            'fields': ('telefon', 'email', 'adresa', 'poznamka'),
            'classes': ('collapse',)
        }),
        ('Moduly', {
            'fields': ('moduly',),
            'description': 'Seznam povolených modulů pro uživatele'
        }),
        ('Časové údaje', {
            'fields': ('datum_vytvoreni',),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:  # Editace existujícího uživatele
            form.base_fields['nove_heslo'].help_text = "Ponechte prázdné pro zachování současného hesla"
        else:  # Vytvoření nového uživatele
            form.base_fields['nove_heslo'].required = True
            form.base_fields['nove_heslo'].help_text = "Heslo je povinné pro nového uživatele"
        return form

@admin.register(ProfilovyObrazek)
class ProfilovyObrazekAdmin(admin.ModelAdmin):
    list_display = ('uzivatel', 'datum_nahrani', 'obrazek_preview')
    list_filter = ('datum_nahrani',)
    search_fields = ('uzivatel__jmeno', 'uzivatel__prijmeni', 'uzivatel__uzivatelske_jmeno')
    readonly_fields = ('datum_nahrani', 'obrazek_preview')
    
    def obrazek_preview(self, obj):
        if obj.obrazek:
            return f'<img src="{obj.obrazek.url}" style="max-height: 50px; max-width: 50px;" />'
        return "Žádný obrázek"
    obrazek_preview.short_description = "Náhled"
    obrazek_preview.allow_tags = True
