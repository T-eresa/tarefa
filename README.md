
Rodar local:

    pip install -r requirements.txt
    python index.py

Deploy:

    npm i -g vercel
    vercel

Os dados ficam no Firebase Realtime Database, sob `/crm` (URL configurável pela variável `FIREBASE_URL`).
A interface web está em `/` e a API JSON nas rotas abaixo.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | /contatos?busca= | Lista/busca contatos |
| POST | /contatos | Cria contato (nome, email, telefone, empresa) |
| GET | /contatos/{id} | Contato + negócios + notas |
| PATCH | /contatos/{id} | Atualiza contato |
| DELETE | /contatos/{id} | Apaga contato (e seus negócios/notas) |
| GET | /negocios?etapa=&contato_id= | Lista negócios |
| POST | /negocios | Cria negócio (contato_id, titulo, valor, etapa) |
| PATCH | /negocios/{id} | Atualiza titulo/valor/etapa |
| DELETE | /negocios/{id} | Apaga negócio |
| GET | /notas?contato_id= | Lista notas |
| POST | /notas | Cria nota (contato_id, texto) |
| GET | /resumo | Funil: totais e valor por etapa |

Etapas: novo, contactado, proposta, ganho, perdido.
