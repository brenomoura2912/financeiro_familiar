import random
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.crypto import get_random_string


def gerar_codigo_convite():
    """Gera código único para convites familiares (requerido pelas migrações)."""
    return get_random_string(8).upper()


class CodigoVerificacaoEmail(models.Model):
    FINALIDADES = (
        ('CADASTRO', 'Ativação de Cadastro'),
        ('ALTERACAO_EMAIL', 'Alteração de E-mail'),
    )

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='codigos_verificacao')
    email = models.EmailField()
    codigo = models.CharField(max_length=6)
    finalidade = models.CharField(max_length=20, choices=FINALIDADES, default='CADASTRO')
    criado_em = models.DateTimeField(auto_now_add=True)
    utilizado = models.BooleanField(default=False)

    def esta_valido(self):
        return not self.utilizado and timezone.now() <= self.criado_em + timedelta(minutes=15)

    @classmethod
    def gerar_codigo(cls, usuario, email, finalidade='CADASTRO'):
        codigo_numerico = f"{random.randint(100000, 999999)}"
        return cls.objects.create(
            usuario=usuario,
            email=email.strip().lower(),
            codigo=codigo_numerico,
            finalidade=finalidade
        )

    def __str__(self):
        return f"{self.usuario.username} - {self.codigo} ({self.finalidade})"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField(upload_to='avatares/', null=True, blank=True)

    @property
    def iniciais(self):
        nome = self.usuario.get_full_name() or self.usuario.username
        partes = [p for p in nome.strip().split() if p]
        if not partes:
            return "U"
        if len(partes) == 1:
            return partes[0][2].upper()
        return (partes[0][0] + partes[-1][0]).upper()
    
    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Familiar(models.Model):
    nome = models.CharField(max_length=150)
    codigo_convite = models.CharField(max_length=20, unique=True, default=gerar_codigo_convite)
    criador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='familias_criadas', null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class VinculoFamiliar(models.Model):
    PAPEIS = (
        ('GESTOR', 'Gestor'),
        ('MEMBRO', 'Membro'),
    )

    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('RECUSADO', 'Recusado'),
    )

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vinculos')
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='membros')
    papel = models.CharField(max_length=20, choices=PAPEIS, default='MEMBRO')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'familiar')

    def __str__(self):
        return f"{self.usuario.username} - {self.familiar.nome} ({self.papel})"


class Categoria(models.Model):
    TIPOS = (
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    )

    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='categorias')
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    icone = models.CharField(max_length=50, default='tag')
    cor = models.CharField(max_length=20, default='#6366f1')

    def __str__(self):
        return f"{self.nome} ({self.familiar.nome})"


class Transacao(models.Model):
    TIPOS = (
        ('RECEITA', 'Receita'),
        ('DESPESA', 'Despesa'),
    )

    FORMAS_PAGAMENTO = (
        ('DINHEIRO', 'Dinheiro'),
        ('PIX', 'PIX'),
        ('CARTAO_CREDITO', 'Cartão de Crédito'),
        ('CARTAO_DEBITO', 'Cartão de Débito'),
        ('TRANSFERENCIA', 'Transferência'),
        ('BOLETO', 'Boleto'),
        ('OUTRO', 'Outro'),
    )

    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='transacoes')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes_criadas')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    data = models.DateField()
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes')
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    comprador = models.CharField(max_length=150, blank=True)
    forma_pagamento = models.CharField(max_length=30, choices=FORMAS_PAGAMENTO, default='PIX')
    comprovante = models.FileField(upload_to='comprovantes/', null=True, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"


class FechamentoMes(models.Model):
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='fechamentos')
    mes = models.PositiveSmallIntegerField()
    ano = models.PositiveIntegerField()
    fechado = models.BooleanField(default=False)
    fechado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fechado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('familiar', 'mes', 'ano')

    def __str__(self):
        return f"{self.familiar.nome} - {self.mes:02d}/{self.ano}"


class LogAuditoria(models.Model):
    transacao = models.ForeignKey(Transacao, on_delete=models.CASCADE, related_name='auditorias')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=50)
    detalhes = models.TextField(blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.acao} em {self.transacao.id} por {self.usuario}"

class CodigoRecuperacaoSenha(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='codigos_recuperacao')
    codigo = models.CharField(max_length=6)
    criado_em = models.DateTimeField(auto_now_add=True)
    utilizado = models.BooleanField(default=False)

    def expirado(self):
        return timezone.now() > self.criado_em + timedelta(minutes=15)

    @classmethod
    def gerar_codigo(cls, user):
        cls.objects.filter(user=user, utilizado=False).update(utilizado=True)
        novo_codigo = f"{random.randint(100000, 999999)}"
        return cls.objects.create(user=user, codigo=novo_codigo)