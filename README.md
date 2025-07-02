# 📚 Projeto Toth - Geração de Livros Educativos

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/status-Estável-brightgreen)
![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-red)
![PDF EPUB Export](https://img.shields.io/badge/export-PDF%20%7C%20EPUB-blueviolet)

---

## 📝 Descrição

**Toth** é uma plataforma para geração de livros ilustrados a partir de imagens, permitindo:

- 📑 Ordenação e reordenação de páginas
- 🔢 Numeração personalizada (romano, moderno, elegante, etc.)
- 🖼️ Inserção automática de logo em capas e contracapas
- 📄 Exportação dos livros em **PDF com sangria** e **EPUB**
- ☁️ Upload final para Google Drive

Ideal para editoras, escolas e produções educacionais rápidas.

---

## 🚀 Tecnologias Utilizadas

- **Python 3.10+**
- **Streamlit** para interface web
- **Pillow** para processamento de imagens
- **ebooklib** para geração de EPUB
- **Google Drive API** para upload automático

---

## 📂 Estrutura do Projeto
```
ProjetoToth/
├── streamlit_app.py
├── assets/
│ ├── thumbs/
│ └── logo.png
├── requirements.txt
└── README.md
```
---

## ⚙️ Instalação

1. Clone o repositório:


git clone https://github.com/seuusuario/ProjetoToth.git
cd ProjetoToth

2. Instale as dependências:
pip install -r requirements.txt

3. Execute o aplicativo Streamlit:
streamlit run streamlit_app.py

Funcionalidades Principais
✅ Upload de imagens em lote
✅ Reordenação dinâmica das páginas
✅ Geração de livros com numeração estilizada
✅ Exportação em ZIP contendo PDF (com e sem sangria) e EPUB
✅ Envio automático ao Google Drive

🤝 Contribuições
Contribuições são bem-vindas! Abra issues ou pull requests com melhorias, novos estilos ou correções.

📄 Licença
Este projeto está licenciado sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.
