import streamlit as st
import openai
import os
import base64
from PIL import Image, ImageDraw, ImageFont
from ebooklib import epub
import io
import zipfile

# ----------------------- Configuração da API do OpenAI -----------------------
import os
openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------------------- Funções Comuns -----------------------
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    else:
        return ""

def int_to_roman(num):
    """Converte número inteiro para algarismos romanos."""
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syms[i]
            num -= val[i]
        i += 1
    return roman_num

def add_page_number(image, display_number, alignment, style="Padrão", custom_color=None):
    """
    Sobrepõe o número (display_number) na parte inferior da imagem,
    aplicando cor e contorno conforme o estilo escolhido e garantindo
    que a numeração esteja a 2cm das margens da página.
    O custom_color (do color picker) pode sobrescrever a cor padrão.
    """
    img = image.copy()
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()

    # Converte para romano se for o estilo "Romano"
    if style == "Romano":
        text = int_to_roman(display_number)
    else:
        text = str(display_number)

    # Ajuste de cor e contorno de cada estilo
    if style == "Padrão":
        fill_color = custom_color if custom_color else "#FFFFFF"
        outline_range = 1
        do_outline = True
    elif style == "Romano":
        fill_color = custom_color if custom_color else "#FFFFFF"
        outline_range = 1
        do_outline = True
    elif style == "Fresco":
        fill_color = custom_color if custom_color else "#FFD700"  # Dourado
        outline_range = 2
        do_outline = True
    elif style == "Moderno":
        fill_color = custom_color if custom_color else "#007BFF"  # Azul
        outline_range = 0
        do_outline = False
    elif style == "Vintage":
        fill_color = custom_color if custom_color else "#A0522D"  # Marrom
        outline_range = 2
        do_outline = True
    elif style == "Elegante":
        fill_color = custom_color if custom_color else "#8E44AD"  # Roxo
        outline_range = 1
        do_outline = True
    else:
        fill_color = custom_color if custom_color else "#FFFFFF"
        outline_range = 1
        do_outline = True

    # Calcula dimensão do texto
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    width, height = img.size

    # Define a margem de 2cm em pixels (assumindo 96 DPI)
    margin = int(2 / 2.54 * 96)  # aproximadamente 75 pixels

    # Calcula a posição horizontal de acordo com o alinhamento
    if alignment == "Esquerda":
        x = margin
    elif alignment == "Direita":
        x = width - text_width - margin
    else:  # Central
        available_width = width - 2 * margin
        x = margin + (available_width - text_width) / 2

    # Posição vertical: 2cm acima da borda inferior
    y = height - text_height - margin

    # Desenha o contorno (outline) se necessário
    if do_outline and outline_range > 0:
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                draw.text((x + dx, y + dy), text, font=font, fill="black")

    # Desenha o texto principal com a cor de preenchimento
    draw.text((x, y), text, font=font, fill=fill_color)

    return img

def generate_pdf(images):
    """Gera um PDF com base em uma lista de objetos PIL.Image."""
    pdf_bytes = io.BytesIO()
    if images:
        images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=images[1:])
    pdf_bytes.seek(0)
    return pdf_bytes

def generate_epub(files, start_page, end_page, initial_number, alignment, number_style, custom_color=None):
    """
    Gera um EPUB com numeração em rodapé para as páginas cujo número
    (posição na ordenação) esteja entre start_page e end_page.
    """
    from ebooklib import epub

    book = epub.EpubBook()
    book.set_identifier("id_livro_123")
    book.set_title("Livro Ilustrado")
    book.set_language("pt")
    book.add_author("Globaltec")

    # Define cores padrão para o rodapé no EPUB
    html_colors = {
        "Padrão": custom_color if custom_color else "#FFFFFF",
        "Romano": custom_color if custom_color else "#FFFFFF",
        "Fresco": custom_color if custom_color else "#FFD700",
        "Moderno": custom_color if custom_color else "#007BFF",
        "Vintage": custom_color if custom_color else "#A0522D",
        "Elegante": custom_color if custom_color else "#8E44AD"
    }

    chapters = []
    for idx, f_dict in enumerate(files):
        page_position = idx + 1
        image_data = f_dict["data"]
        image_filename = f"image_{idx}.jpg"

        epub_img = epub.EpubItem(
            uid=image_filename,
            file_name=image_filename,
            media_type="image/jpeg",
            content=image_data
        )
        book.add_item(epub_img)

        # Verifica se a página atual entra no intervalo para receber numeração
        if start_page <= page_position <= end_page:
            display_number = initial_number + (page_position - start_page)
            if number_style == "Romano":
                display_text = int_to_roman(display_number)
            else:
                display_text = str(display_number)

            html_color = html_colors.get(number_style, "#FFFFFF")
            if alignment == "Esquerda":
                align_style = "text-align:left; margin-left:75px;"  # 75px ≈ 2cm
            elif alignment == "Direita":
                align_style = "text-align:right; margin-right:75px;"
            else:
                align_style = "text-align:center; margin:0 75px;"
            number_html = f"<div style='{align_style} font-size:16px; margin-top:10px; color:{html_color};'>{display_text}</div>"
        else:
            number_html = ""

        c = epub.EpubHtml(
            title=f"Página {page_position}",
            file_name=f"page_{idx}.xhtml",
            lang="pt"
        )
        c.content = f"""
        <html>
          <head>
            <meta charset="utf-8" />
            <title>Página {page_position}</title>
          </head>
          <body>
            <h1>Página {page_position}</h1>
            <img src="{image_filename}" alt="Página {page_position}" style="width:100%;"/>
            {number_html}
          </body>
        </html>
        """
        book.add_item(c)
        chapters.append(c)

    # Ajusta estrutura do EPUB
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub_bytes = io.BytesIO()
    epub.write_epub(epub_bytes, book)
    epub_bytes.seek(0)
    return epub_bytes

def move_page(file_index, new_position):
    """Remove a página da posição atual e insere na nova posição (1-based)."""
    order = st.session_state.order
    current_pos = order.index(file_index)
    order.pop(current_pos)
    new_index = max(0, min(new_position - 1, len(order)))
    order.insert(new_index, file_index)
    st.session_state.order = order
    st.rerun()

def chunk_list(seq, chunk_size=7):
    """Divide a lista seq em sub-listas de tamanho chunk_size."""
    for i in range(0, len(seq), chunk_size):
        yield seq[i:i + chunk_size]

# ----------------------- Página do Gerador de Livros -----------------------
def book_page():
    # Exibe a logo centralizada (caso queira usar uma logo, coloque o arquivo 'logo.png' no diretório)
    logo_base64 = get_base64_image("logo.png")
    if logo_base64:
        st.markdown(
            f"""
            <div style="text-align:center;">
                <img src="data:image/png;base64,{logo_base64}" style="width:230px; margin-bottom:-10px;" />
            </div>
            """,
            unsafe_allow_html=True
        )
    st.title("Projeto Thoth - Geração de Livros")
    st.write("""
    Selecione as imagens do livro. Você pode selecionar uma ou várias páginas.
    Para cada página, insira o número da posição desejada e clique em **Atualizar posição** para mover a página.
    Se uma página for inserida em uma posição já ocupada, as outras serão deslocadas.
    
    Em seguida, defina:
      - O intervalo de páginas a serem numeradas (por posição na ordenação).
      - O número inicial que aparecerá na primeira página numerada.
      - O estilo de numeração desejado (Padrão, Romano, Fresco, Moderno, Vintage ou Elegante).
      - O alinhamento da numeração (Esquerda, Central ou Direita).
      - Escolha a cor desejada para a numeração (pode sobrescrever a cor padrão do estilo).
    
    Clique em **Gerar Livro** para produzir um PDF e um EPUB empacotados em um ZIP.
    """)

    uploaded_files = st.file_uploader("Escolha as imagens", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        # Modificação para adicionar novas páginas sem sobrescrever as já carregadas
        if 'file_data' not in st.session_state:
            st.session_state.file_data = []
            st.session_state.order = []

        # Cria um conjunto com os nomes dos arquivos já existentes
        existing_names = {f["name"] for f in st.session_state.file_data}

        # Filtra os novos arquivos que ainda não foram adicionados
        new_files = [f for f in uploaded_files if f.name not in existing_names]

        # Adiciona os novos arquivos e atualiza a ordem (acrescenta ao final)
        for f in new_files:
            st.session_state.file_data.append({
                "name": f.name,
                "data": f.read()
            })
            st.session_state.order.append(len(st.session_state.file_data) - 1)

    if 'file_data' in st.session_state and st.session_state.file_data:
        order = st.session_state.order

        st.write("### Reordene as páginas (7 por linha)")
        for row_chunk in chunk_list(order, 7):
            cols = st.columns(len(row_chunk))
            for idx, col in enumerate(cols):
                file_index = row_chunk[idx]
                f_dict = st.session_state.file_data[file_index]
                image = Image.open(io.BytesIO(f_dict["data"]))
                col.image(image, use_container_width=True)

                current_position = order.index(file_index) + 1
                new_pos = col.number_input(
                    "Posição",
                    min_value=1,
                    max_value=len(order),
                    value=current_position,
                    key=f"pos_{file_index}"
                )
                if col.button("Atualizar posição", key=f"update_{file_index}"):
                    move_page(file_index, new_pos)

        num_pages = len(order)
        st.write("### Defina a numeração")
        num_start = st.number_input(
            "Início da numeração (posição)",
            min_value=1,
            max_value=num_pages,
            value=1,
            key="num_start"
        )
        num_end = st.number_input(
            "Última página a ser numerada (posição)",
            min_value=1,
            max_value=num_pages,
            value=num_pages,
            key="num_end"
        )
        if num_start > num_end:
            st.error("O início não pode ser maior que o fim.")
        initial_number = st.number_input("Número inicial", min_value=1, value=1, key="initial_number")

        # Seleção do estilo (apenas os 6 da miniatura)
        number_styles = ["Padrão", "Romano", "Fresco", "Moderno", "Vintage", "Elegante"]
        number_style = st.selectbox("Estilo de numeração", number_styles, index=0)

        # Mostra miniatura específica de cada estilo
        style_thumbnails = {
            "Padrão": "thumb_padrao.png",
            "Romano": "thumb_romano.png",
            "Fresco": "thumb_fresco.png",
            "Moderno": "thumb_moderno.png",
            "Vintage": "thumb_vintage.png",
            "Elegante": "thumb_elegante.png"
        }
        thumb_path = style_thumbnails.get(number_style, "")
        thumb_base64 = get_base64_image(thumb_path)
        if thumb_base64:
            st.markdown(
                f"""
                <div style="text-align:center;">
                    <img src="data:image/png;base64,{thumb_base64}" style="width:100px;" />
                </div>
                """,
                unsafe_allow_html=True
            )

        # Color picker para todos os estilos
        custom_color = st.color_picker("Escolha a cor para a numeração", value="#FFFFFF")

        alignment = st.selectbox("Alinhamento da numeração", ["Esquerda", "Central", "Direita"], index=1)

        # Botão para gerar PDF + EPUB em ZIP
        if st.button("Gerar Livro"):
            reordered_files = [st.session_state.file_data[i] for i in st.session_state.order]

            # Converte cada arquivo para PIL.Image e, se necessário, para RGB
            image_list = []
            for f_dict in reordered_files:
                img = Image.open(io.BytesIO(f_dict["data"]))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                image_list.append(img)

            # Aplica numeração conforme o intervalo definido
            for j in range(len(image_list)):
                page_position = j + 1
                if num_start <= page_position <= num_end:
                    display_number = initial_number + (page_position - num_start)
                    image_list[j] = add_page_number(
                        image_list[j],
                        display_number,
                        alignment,
                        style=number_style,
                        custom_color=custom_color
                    )

            # Gera PDF
            pdf_bytes = generate_pdf(image_list)

            # Gera EPUB
            epub_bytes = generate_epub(
                reordered_files,
                num_start,
                num_end,
                initial_number,
                alignment,
                number_style,
                custom_color=custom_color
            )

            # Empacota tudo em um ZIP
            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, mode="w") as zipf:
                zipf.writestr("livro.pdf", pdf_bytes.getvalue())
                zipf.writestr("livro.epub", epub_bytes.getvalue())
            zip_bytes.seek(0)

            # Disponibiliza para download
            st.download_button(
                "Baixar ZIP",
                data=zip_bytes,
                file_name="livro.zip",
                mime="application/zip"
            )

if __name__ == "__main__":
    book_page()
