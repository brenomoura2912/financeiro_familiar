import os
import secrets
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


def gerar_codigo_convite():
    return secrets.token_hex(4).upper()


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"

    @property
    def iniciais(self):
        nome = self.usuario.get_full_name().strip() or self.usuario.username.strip()
        partes = nome.split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[-1][0]).upper()
        elif partes:
            return partes[0][:2].upper()
        return "U"


@receiver(post_save, sender=User)
def criar_ou_salvar_perfil(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(usuario=instance)
    else:
        if hasattr(instance, 'perfil'):
            instance.perfil.save()
        else:
            PerfilUsuario.objects.create(usuario=instance)


class Familiar(models.Model):
    nome = models.CharField(max_length=150)
    codigo_convite = models.CharField(max_length=20, unique=True, default=gerar_codigo_convite)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome


class VinculoFamiliar(models.Model):
    PAPEL_CHOICES = (
        ('GESTOR', 'Gestor'),
        ('MEMBRO', 'Membro'),
    )
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vinculos')
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='vinculos')
    papel = models.CharField(max_length=10, choices=PAPEL_CHOICES, default='MEMBRO')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('usuario', 'familiar')

    def __str__(self):
        return f"{self.usuario.username} -> {self.familiar.nome} ({self.papel} - {self.status})"


class Categoria(models.Model):
    TIPO_CHOICES = (
        ('ENTRADA', 'Entrada (Receita)'),
        ('SAIDA', 'Saída (Despesa)'),
    )
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='categorias', null=True, blank=True)
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='SAIDA')

    class Meta:
        unique_together = ('familiar', 'nome')
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class Transacao(models.Model):
    TIPO_CHOICES = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    )
    FORMAS_PAGAMENTO = (
        ('PIX', 'Pix'),
        ('CARTAO_CREDITO', 'Cartão de Crédito'),
        ('CARTAO_DEBITO', 'Cartão de Débito'),
        ('DINHEIRO', 'Dinheiro'),
        ('TRANSFERENCIA', 'Transferência'),
        ('OUTRO', 'Outro'),
    )

    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='transacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    data = models.DateField()
    descricao = models.CharField(max_length=255)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes')
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    comprador = models.CharField(max_length=100)
    forma_pagamento = models.CharField(max_length=20, choices=FORMAS_PAGAMENTO, default='PIX')
    comprovante = models.FileField(upload_to='comprovantes/', null=True, blank=True)
    observacoes = models.TextField(null=True, blank=True)

    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transacoes_criadas')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.data} - {self.descricao} (R$ {self.valor})"


class FechamentoCompetencia(models.Model):
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='fechamentos')
    ano = models.IntegerField()
    mes = models.IntegerField()
    fechado = models.BooleanField(default=True)
    fechado_em = models.DateTimeField(auto_now=True)
    fechado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('familiar', 'ano', 'mes')

    def __str__(self):
        return f"{self.familiar.nome} - {self.mes:02d}/{self.ano} ({'Fechado' if self.fechado else 'Aberto'})"


class LogAuditoriaTransacao(models.Model):
    ACAO_CHOICES = (
        ('CRIACAO', 'Criação'),
        ('EDICAO', 'Edição'),
        ('EXCLUSAO', 'Exclusão'),
    )
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='logs_auditoria')
    transacao_id_ref = models.IntegerField()
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=10, choices=ACAO_CHOICES)
    detalhes = models.TextField()
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.acao}] Ref #{self.transacao_id_ref} por {self.usuario}"