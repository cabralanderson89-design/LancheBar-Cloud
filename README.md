# LancheBar Cloud

Sistema acadêmico de gestão de lanchonete e bar, com foco em controle de estoque por lote, datas de validade, mesas, pedidos, cozinha e caixa.

## Arquitetura
- Interface web responsiva (HTML, CSS, JavaScript)
- API Python com FastAPI
- Banco SQLite para demonstração local; PostgreSQL para implantação na nuvem
- Hospedagem gerenciada planejada no Render
- Emissão fiscal prevista para etapa futura, ainda não implementada

## Situação
Projeto em desenvolvimento para apresentação acadêmica. **Não está homologado para operação comercial**. Ainda requer testes, melhorias de segurança, impressão térmica automática, migrações, backups e validação do fluxo financeiro.

## Executar localmente
1. Instale Python 3.12+
2. Execute `pip install -r requirements.txt`
3. Configure `ADMIN_PASSWORD` no ambiente com uma senha forte
4. Execute `uvicorn app.main:app --reload`
5. Acesse `http://127.0.0.1:8000`

## Código e documentação
A versão de demonstração será adicionada progressivamente neste repositório. Não publique arquivos `.env`, senhas ou bancos de dados reais.
