from django import forms
from django.db.models import Q
from django.contrib.auth.models import User
from .models import Transacao, Familiar, Categoria

class CadastroUsuarioForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500'}),
        label="Senha"
    )

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password']
        labels = {
            'first_name': 'Nome Completo',
            'username': 'Nome de Usuário (Login)',
            'email': 'E-mail',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500'}),
            'username': forms.TextInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500'}),
        }


class FamiliarForm(forms.ModelForm):
    class Meta:
        model = Familiar
        fields = ['nome', 'data_nascimento']
        labels = {
            'nome': 'Nome do Familiar',
            'data_nascimento': 'Data de Nascimento (opcional)',
        }
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500',
                'placeholder': 'Ex: Dona Francisca, Seu Manoel'
            }),
            'data_nascimento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm focus:ring-2 focus:ring-indigo-500'
            }),
        }


class EntrarFamiliaForm(forms.Form):
    codigo_convite = forms.CharField(
        max_length=10,
        label="Código de Convite da Família",
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-sm font-mono tracking-widest text-center uppercase focus:ring-2 focus:ring-indigo-500',
            'placeholder': 'Ex: A1B2C3'
        })
    )


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = ['tipo', 'data', 'descricao', 'valor', 'categoria', 'comprador', 'forma_pagamento', 'comprovante', 'observacoes']
        widgets = {
            'tipo': forms.Select(attrs={'id': 'id_tipo_lancamento', 'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm'}),
            'descricao': forms.TextInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm', 'placeholder': 'Ex: Medicamentos contínuos, Feira'}),
            'valor': forms.NumberInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm', 'placeholder': '0.00', 'step': '0.01'}),
            'categoria': forms.Select(attrs={'id': 'id_categoria_select', 'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm'}),
            'comprador': forms.TextInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm', 'placeholder': 'Ex: Jean Viana'}),
            'forma_pagamento': forms.Select(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm'}),
            'comprovante': forms.FileInput(attrs={'class': 'w-full border border-slate-300 rounded-lg p-1.5 bg-slate-50 text-xs text-slate-700'}),
            'observacoes': forms.Textarea(attrs={'class': 'w-full border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 text-sm', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        familiar = kwargs.pop('familiar', None)
        super().__init__(*args, **kwargs)
        if familiar:
            self.fields['categoria'].queryset = Categoria.objects.filter(
                Q(familiar__isnull=True) | Q(familiar=familiar)
            )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        categoria = cleaned_data.get('categoria')

        if categoria and tipo and categoria.tipo != tipo:
            tipo_label = "Saída" if tipo == "SAIDA" else "Entrada"
            self.add_error('categoria', f'Esta categoria não pertence ao tipo {tipo_label}.')
        return cleaned_data