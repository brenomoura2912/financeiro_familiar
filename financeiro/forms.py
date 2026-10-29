from django import forms
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from .models import Familiar, Transacao, Categoria, PerfilUsuario


def validar_formato_email_estrito(email_valor):
    """Garante formato de e-mail válido com domínio e extensão completas."""
    if not email_valor:
        raise ValidationError("O endereço de e-mail é obrigatório.")
    
    validador = EmailValidator(message="Insira um endereço de e-mail válido (ex: utilizador@dominio.com).")
    validador(email_valor)

    partes = email_valor.split('@')
    if len(partes) != 2 or '.' not in partes[1]:
        raise ValidationError("O domínio do e-mail deve conter uma extensão válida (ex: .com, .com.br).")


class CadastroForm(forms.ModelForm):
    nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: João da Silva',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'exemplo@gmail.com',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'usuario123',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def full_clean(self):
        """Limpa registros fantasmas inativos ANTES da verificação de unicidade do Django."""
        if self.is_bound:
            email = self.data.get('email', '').strip().lower()
            username = self.data.get('username', '').strip()
            if email:
                User.objects.filter(email__iexact=email, is_active=False).delete()
            if username:
                User.objects.filter(username__iexact=username, is_active=False).delete()
        super().full_clean()

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("O nome de utilizador é obrigatório.")
        if User.objects.filter(username__iexact=username, is_active=True).exists():
            raise forms.ValidationError("Este nome de utilizador já se encontra registado.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        validar_formato_email_estrito(email)
        if User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("Este e-mail já se encontra registado.")
        return email

    def save(self, commit=True):
        username = self.cleaned_data['username'].strip()
        email = self.cleaned_data['email'].strip().lower()

        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.email = email
        user.username = username
        user.is_active = False

        nome_completo = self.cleaned_data.get('nome_completo', '').strip()
        partes = nome_completo.split(' ', 1)
        user.first_name = partes[0]
        user.last_name = partes[1] if len(partes) > 1 else ''

        if commit:
            user.save()
        return user  
        nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: João da Silva',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'exemplo@gmail.com',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'usuario123',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500 transition shadow-sm'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("O nome de utilizador é obrigatório.")
        if User.objects.filter(username__iexact=username, is_active=True).exists():
            raise forms.ValidationError("Este nome de utilizador já se encontra registado.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        validar_formato_email_estrito(email)
        if User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("Este e-mail já se encontra registado.")
        return email

    def save(self, commit=True):
        username = self.cleaned_data['username'].strip()
        email = self.cleaned_data['email'].strip().lower()

        User.objects.filter(email__iexact=email, is_active=False).delete()
        User.objects.filter(username__iexact=username, is_active=False).delete()

        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.email = email
        user.username = username
        user.is_active = False

        nome_completo = self.cleaned_data.get('nome_completo', '').strip()
        partes = nome_completo.split(' ', 1)
        user.first_name = partes[0]
        user.last_name = partes[1] if len(partes) > 1 else ''

        if commit:
            user.save()
        return user


class EditarPerfilForm(forms.ModelForm):
    nome_completo = forms.CharField(
        label="Nome Completo",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    username = forms.CharField(
        label="Nome de Usuário",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    email = forms.EmailField(
        label="E-mail",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    foto = forms.ImageField(
        label="Foto de Perfil",
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full text-xs text-slate-500 dark:text-slate-400 file:mr-3 file:py-2 file:px-3.5 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-slate-700 dark:file:text-slate-200 cursor-pointer'
        })
    )

    class Meta:
        model = User
        # Removemos 'email' daqui para impedir que o Django salve direto no banco
        fields = ['username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            nome_existente = self.instance.get_full_name().strip() or self.instance.first_name
            self.fields['nome_completo'].initial = nome_existente
            self.fields['email'].initial = self.instance.email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso por outra conta.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado em outra conta.")
        return email

    def save(self, commit=True):
        nome_completo = self.cleaned_data.get('nome_completo', '').strip()
        user = super().save(commit=False)
        
        partes_nome = nome_completo.split(' ', 1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        # GARANTIA: O e-mail nunca é salvo aqui. Fica travado no original da instância.
        user.email = self.instance.email

        if commit:
            user.save()

        foto = self.cleaned_data.get('foto')
        if foto and hasattr(user, 'perfil'):
            perfil = user.perfil
            perfil.foto = foto
            perfil.save()

        return user
        nome_completo = forms.CharField(
        label="Nome Completo",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    username = forms.CharField(
        label="Nome de Usuário",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    email = forms.EmailField(
        label="E-mail",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    foto = forms.ImageField(
        label="Foto de Perfil",
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full text-xs text-slate-500 dark:text-slate-400 file:mr-3 file:py-2 file:px-3.5 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-slate-700 dark:file:text-slate-200 cursor-pointer'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            nome_existente = self.instance.get_full_name().strip() or self.instance.first_name
            self.fields['nome_completo'].initial = nome_existente

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso por outra conta.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado em outra conta.")
        return email

    def save(self, commit=True):
        email_digitado = self.cleaned_data.get('email', '').strip().lower()
        email_antigo = self.instance.email
        nome_completo = self.cleaned_data.get('nome_completo', '').strip()

        user = super().save(commit=False)
        
        # Divide o nome completo entre first_name e last_name
        partes_nome = nome_completo.split(' ', 1)
        user.first_name = partes_nome[0]
        user.last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        # Mantém o e-mail original se tiver sido digitado um novo (aguarda confirmação por código)
        if email_digitado != email_antigo:
            user.email = email_antigo

        if commit:
            user.save()

        foto = self.cleaned_data.get('foto')
        if foto and hasattr(user, 'perfil'):
            perfil = user.perfil
            perfil.foto = foto
            perfil.save()

        return user
        first_name = forms.CharField(
        label="Nome Completo",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    username = forms.CharField(
        label="Nome de Usuário",
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    email = forms.EmailField(
        label="E-mail",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-800 dark:text-slate-100 text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
        })
    )
    foto = forms.ImageField(
        label="Foto de Perfil",
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'w-full text-xs text-slate-500 dark:text-slate-400 file:mr-3 file:py-2 file:px-3.5 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:file:bg-slate-700 dark:file:text-slate-200 cursor-pointer'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso por outra conta.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado em outra conta.")
        return email

    def save(self, commit=True):
        # Impede a gravação direta do email se tiver mudado
        email_digitado = self.cleaned_data.get('email', '').strip().lower()
        email_antigo = self.instance.email

        user = super().save(commit=False)
        if email_digitado != email_antigo:
            user.email = email_antigo  # Mantém o e-mail atual até ser confirmado

        if commit:
            user.save()

        foto = self.cleaned_data.get('foto')
        if foto:
            perfil = user.perfil
            perfil.foto = foto
            perfil.save()

        return user  
        nome_completo = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-700/60 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm text-slate-800 dark:text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500'
        })
    )
    foto = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'input-avatar-upload',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nome_completo'].initial = self.instance.get_full_name()
            if hasattr(self.instance, 'perfil') and self.instance.perfil.foto:
                self.fields['foto'].initial = self.instance.perfil.foto

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError("O nome de utilizador é obrigatório.")
        if User.objects.filter(username__iexact=username, is_active=True).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este nome de utilizador já está a ser utilizado.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        validar_formato_email_estrito(email)
        if User.objects.filter(email__iexact=email, is_active=True).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Este e-mail já está associado a outra conta.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        nome_completo = self.cleaned_data.get('nome_completo', '').strip()
        partes = nome_completo.split(' ', 1)
        user.first_name = partes[0]
        user.last_name = partes[1] if len(partes) > 1 else ''
        user.email = self.cleaned_data['email'].strip().lower()

        if commit:
            user.save()
            perfil, _ = PerfilUsuario.objects.get_or_create(usuario=user)
            foto_enviada = self.cleaned_data.get('foto')
            if foto_enviada:
                perfil.foto = foto_enviada
                perfil.save()
        return user


class FamiliarForm(forms.ModelForm):
    class Meta:
        model = Familiar
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Ex: Dona Maria de Lourdes',
                'class': 'w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium'
            })
        }


class EntrarFamiliaForm(forms.Form):
    codigo_convite = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'EX: LUR83921',
            'class': 'w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-700 text-slate-800 dark:text-slate-100 border border-slate-300 dark:border-slate-600 rounded-xl text-xs sm:text-sm uppercase tracking-wider outline-none focus:ring-2 focus:ring-indigo-500 font-mono font-medium'
        })
    )


class TransacaoForm(forms.ModelForm):
    class Meta:
        model = Transacao
        fields = [
            'tipo', 'data', 'descricao', 'categoria', 
            'valor', 'comprador', 'forma_pagamento', 
            'comprovante', 'observacoes'
        ]
        widgets = {
            'tipo': forms.Select(attrs={
                'id': 'id_tipo_lancamento',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'data': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'descricao': forms.TextInput(attrs={
                'placeholder': 'Ex: Compras do mês, Farmácia',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'categoria': forms.Select(attrs={
                'id': 'id_categoria_select',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'valor': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': '0.00',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'comprador': forms.TextInput(attrs={
                'placeholder': 'Quem realizou a compra?',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'forma_pagamento': forms.Select(attrs={
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
            'comprovante': forms.FileInput(attrs={
                'class': 'w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 dark:file:bg-indigo-950 dark:file:text-indigo-300 hover:file:bg-indigo-100 cursor-pointer'
            }),
            'observacoes': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Observações complementares...',
                'class': 'w-full px-3 py-2 bg-slate-50 dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        familiar = kwargs.pop('familiar', None)
        super().__init__(*args, **kwargs)
        if familiar:
            self.fields['categoria'].queryset = Categoria.objects.filter(familiar=familiar)