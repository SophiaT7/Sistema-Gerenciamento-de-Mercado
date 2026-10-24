# Sistema de Gerenciamento de Mercado & Ponto de Venda (PDV)

> **Trabalho de Programação para Internet & Engenharia de Software**  
> Desenvolvido em **Django**, baseado na modelagem UML extraída de `classesMercadoTipos.asta` com padrão arquitetural **BCE (Boundary - Control - Entity)** e interface administrativa moderna com **Django Jazzmin**.

---

## 🏛️ 1. Padrão Arquitetural BCE (Boundary - Control - Entity)

O sistema foi estruturado seguindo rigorosamente a modelagem de robustez e o diagrama de classes da Engenharia de Software:

| Camada BCE | Papel no Sistema | Equivalente Django / Arquivos |
| :--- | :--- | :--- |
| **`<<entity>>` (Entidade)** | Representa os dados e regras intrínsecas de persistência no banco SQL. | `mercado/models.py`<br>*(Usuario, Produto, Lote, EntradaMercadoria, Caixa, Venda, ItemVenda, Perda, MovimentacaoEstoque, Alerta)* |
| **`<<control>>` (Controlador)** | Orquestra as regras de negócio, fluxos transacionais, cálculo de margens, baixa FEFO de estoque e conciliação de caixa. | `mercado/services.py`<br>*(ControladorProduto, ControladorEntradaMercadoria, ControladorCaixa, ControladorVenda, ControladorPerda, ControladorAlertas, ControladorAutenticacao)* |
| **`<<boundary>>` (Fronteira)** | Interfaces pelas quais os atores humanos interagem com o sistema. | `mercado/views.py` & `templates/mercado/`<br>*(TelaLogin, Dashboard, TelaCadastroProduto, TelaEntradaMercadoria, TelaCaixa, TelaPDV, TelaRegistroPerda, TelaAlertas)* |

---

## 📋 2. Requisitos de Engenharia de Software

### Requisitos Funcionais (RF)
* **RF01 - Autenticação por Papel:** Autenticar usuários e restringir acessos de acordo com o papel (`Dono`, `Gerente`, `Operador de Caixa`, `Estoquista`).
* **RF02 - Gestão de Produtos e Preços:** Cadastro de produtos com código de barras, categoria, estoque mínimo, preço de custo, margem de lucro e preço de venda com recálculo automático.
* **RF03 - Entrada por Nota Fiscal com Lotes:** Registrar entrada de mercadorias com múltiplos lotes, quantidades, custos e datas de validade.
* **RF04 - Ponto de Venda (PDV) com Baixa Inteligente (FEFO):** Venda ágil com busca por código/nome, cálculo de troco para dinheiro, PIX e cartões, com baixa automática priorizando os lotes mais próximos do vencimento (*First Expired, First Out*).
* **RF05 - Abertura e Fechamento de Caixa:** Abertura com fundo de troco inicial e fechamento com valor físico contado, gerando conciliação automática com o valor do sistema (apontando sobra ou quebra).
* **RF06 - Auditoria e Registro de Perdas:** Registrar perdas (motivos: vencimento, avaria, furto) com redução imediata do estoque e rastreamento do responsável.
* **RF07 - Central de Alertas Ativa:** Notificar produtos abaixo do estoque mínimo, lotes vencidos ou próximos de vencer e quebras de caixa, com opção de marcar como visto.

### Requisitos Não Funcionais (RNF)
* **RNF01 - Banco de Dados SQL:** Relacional com integridade referencial (SQLite em desenvolvimento e PostgreSQL para deploy).
* **RNF02 - Usabilidade & Estética:** Interface web responsiva, atalhos de teclado para PDV (F4 para finalizar, Enter para bipar), feedback visual em tempo real.
* **RNF03 - Admin Moderno:** Painel Django Admin estilizado via **Jazzmin** com suporte a modo escuro/claro e navegação rápida.
* **RNF04 - Deploy Gratuito:** Preparado para hospedagem gratuita (Render ou PythonAnywhere).

---

## 👥 3. Usuários Padrão para Demonstração

O banco de dados já possui dados de teste populados:

| Usuário | Senha | Papel | Acessos |
| :--- | :--- | :--- | :--- |
| **`dono`** | `dono123` | **Dono do Mercado** | Acesso total ao Dashboard, Produtos, Entradas, Alertas, Perdas e Admin Jazzmin. |
| **`operador`** | `caixa123` | **Operador de Caixa** | Acesso direto ao PDV e Abertura/Fechamento de Caixa. |
| **`gerente`** | `gerente123` | **Gerente** | Gestão de produtos, entradas, perdas e caixas. |

---

## 🚀 4. Como Executar Localmente

1. **Ativar o Ambiente Virtual:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
2. **Executar as Migrações (se necessário):**
   ```powershell
   python manage.py migrate
   ```
3. **Popular Dados Iniciais (se desejar resetar/repopular):**
   ```powershell
   python manage.py seed_data
   ```
4. **Rodar os Testes Unitários de Engenharia de Software:**
   ```powershell
   python manage.py test mercado
   ```
5. **Iniciar o Servidor:**
   ```powershell
   python manage.py runserver
   ```
   * Acesso à aplicação: `http://127.0.0.1:8000/`
   * Painel Administrativo Jazzmin: `http://127.0.0.1:8000/admin/`

---

## ☁️ 5. Guia para Servidor Gratuito (Deploy)

### Opção 1: Render.com (Recomendado)
1. Crie um repositório no GitHub e envie o código do projeto:
   ```bash
   git init
   git add .
   git commit -m "Sistema de Mercado Django BCE"
   git push origin main
   ```
2. Acesse [render.com](https://render.com) e conecte sua conta GitHub.
3. Crie um **New Web Service**:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_data`
   * **Start Command:** `gunicorn config.wsgi:application`
4. Crie uma instância de **PostgreSQL** gratuita no Render (se quiser banco externo) e adicione a variável `DATABASE_URL` no Web Service.

### Opção 2: PythonAnywhere (Muito simples)
1. Crie uma conta gratuita em [pythonanywhere.com](https://www.pythonanywhere.com).
2. Na aba **Consoles**, faça `git clone` do seu repositório.
3. Na aba **Web**, selecione `Manual Configuration` com Python 3.10+, aponte para o virtualenv e configure o arquivo WSGI.
