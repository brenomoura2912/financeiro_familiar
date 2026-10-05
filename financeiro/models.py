import uuid
from django.db import models
from django.contrib.auth.models import User

def gerar_codigo_convite():
    return uuid.uuid4().hex[:6].upper()

class Familiar(models.Model):
    nome = models.CharField(max_length=150, verbose_name="Nome do Familiar")
    data_nascimento = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    codigo_convite = models.CharField(
        max_length=10, 
        unique=True, 
        default=gerar_codigo_convite, 
        verbose_name="Código de Convite da Família"
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Familiar"
        verbose_name_plural = "Familiares"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} (Código: {self.codigo_convite})"


class VinculoFamiliar(models.Model):
    PAPEIS = [
        ('GESTOR', 'Gestor Principal (Controle Total)'),
        ('MEMBRO', 'Membro Familiar (Lança despesas e visualiza)'),
    ]

    STATUS = [
        ('PENDENTE', 'Aguardando Aprovação do Gestor'),
        ('APROVADO', 'Aprovado / Ativo'),
        ('RECUSADO', 'Recusado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vinculos')
    familiar = models.ForeignKey(Familiar, on_delete=models.CASCADE, related_name='membros_vinculados')
    papel = models.CharField(max_length=15, choices=PAPEIS, default='MEMBRO')
    status = models.CharField(max_length=15, choices=STATUS, default='PENDENTE')
    solicitado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('usuario', 'familiar')
        verbose_name = "Vínculo Familiar"
        verbose_name_plural = "Vínculos Familiares"

    def __str__(self):
        return f"{self.usuario.username} -> {self.familiar.nome} [{self.papel} - {self.status}]"


class Categoria(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Rendimento / Entrada'),
        ('SAIDA', 'Despesa / Saída'),
    ]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    familiar = models.ForeignKey(
        Familiar, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='categorias_customizadas'
    )

    class Meta:
        ordering = ['nome']
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        origem = f" ({self.familiar.nome})" if self.familiar else " (Padrão)"
        return f"{self.nome} - {self.get_tipo_display()}{origem}"


class TransacaoManager(models.Manager):
    def para_familiar(self, familiar):
        return self.filter(familiar=familiar)


class Transacao(models.Model):
    FORMAS_PAGAMENTO = [
        ('DEBITO', 'Cartão de Débito'),
        ('CREDITO', 'Cartão de Crédito'),
        ('PIX', 'PIX'),
        ('DINHEIRO', 'Dinheiro em Espécie'),
        ('TRANSFERENCIA', 'Transferência Bancária'),
    ]

    TIPO_TRANSACAO = [
        ('ENTRADA', 'Entrada (Aposentadoria / Benefício)'),
        ('SAIDA', 'Saída (Despesa / Compra)'),
    ]

    familiar = models.ForeignKey(
        Familiar, 
        on_delete=models.CASCADE, 
        related_name='transacoes', 
        verbose_name="Familiar"
    )
    tipo = models.CharField(max_length=10, choices=TIPO_TRANSACAO, default='SAIDA', verbose_name="Tipo de Lançamento")
    descricao = models.CharField(max_length=255, verbose_name="Descrição / Finalidade")
    valor = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor (R$)")
    data = models.DateField(verbose_name="Data do Lançamento")
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='transacoes', verbose_name="Categoria")
    comprador = models.CharField(max_length=120, verbose_name="Responsável / Comprador", help_text="Ex: Jean Viana, Cuidadora Maria, etc.")
    forma_pagamento = models.CharField(max_length=20, choices=FORMAS_PAGAMENTO, default='DEBITO', verbose_name="Forma de Pagamento")
    comprovante = models.FileField(upload_to='comprovantes/%Y/%m/', null=True, blank=True, verbose_name="Nota Fiscal / Comprovante (PDF ou Imagem)")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lancamentos_criados', verbose_name="Criado por")
    criado_em = models.DateTimeField(auto_now_add=True)

    objects = TransacaoManager()

    class Meta:
        ordering = ['-data', '-criado_em']
        verbose_name = "Transação"
        verbose_name_plural = "Transações"

    def __str__(self):
        return f"[{self.familiar.nome}] {self.data.strftime('%d/%m/%Y')} - {self.descricao} - R$ {self.valor}"