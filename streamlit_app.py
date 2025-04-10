import streamlit as st
import openai
import os
import base64
from PIL import Image, ImageDraw, ImageFont
from ebooklib import epub
import io
import zipfile

# ------------------ Integração com Google Drive ------------------
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

def upload_to_drive(file_bytes, filename, folder_id=None):
    """
    Faz upload do arquivo para o Google Drive usando credenciais de serviço.
    Se folder_id for fornecido, o arquivo é enviado para essa pasta específica.
    """
    SCOPES = ['https://www.googleapis.com/auth/drive']
    credentials = service_account.Credentials.from_service_account_file(
        'service_account.json', scopes=SCOPES)
    service = build('drive', 'v3', credentials=credentials)
    
    file_metadata = {
        'name': filename,
        'mimeType': 'application/zip'
    }
    if folder_id:
        file_metadata['parents'] = [folder_id]
    
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='application/zip')
    file = service.files().create(
        body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

# ------------------------ Configuração da API OpenAI ------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    else:
        return ""

def int_to_roman(num):
    """Converte número inteiro para algarismos romanos."""
    val = [1000, 900, 500, 400,
           100, 90, 50, 40,
           10, 9, 5, 4,
           1]
    syms = ["M", "CM", "D", "CD",
            "C", "XC", "L", "XL",
            "X", "IX", "V", "IV",
            "I"]
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
    """
    img = image.copy()
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()
    
    text = int_to_roman(display_number) if style == "Romano" else str(display_number)
    
    if style == "Padrão":
        fill_color = custom_color if custom_color else "#FFFFFF"
        outline_range = 1
        do_outline = True
    elif style == "Romano":
        fill_color = custom_color if custom_color else "#FFFFFF"
        outline_range = 1
        do_outline = True
    elif style == "Fresco":
        fill_color = custom_color if custom_color else "#FFD700"
        outline_range = 2
        do_outline = True
    elif style == "Moderno":
        fill_color = custom_color if custom_color else "#007BFF"
        outline_range = 0
        do_outline = False
    elif style == "Vintage":
        fill_color = custom_color if custom_color else "#A0522D"
        outline_range = 2
        do_outline = True
    elif style == "Elegante":
        fill_color = custom_color if custom_color else "#8E44AD"
        outline_range = 1
        do_outline = True
    else:
        fill_color = custom_color if custom_color else "#FFFFFF"
        outline_range = 1
        do_outline = True

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    width, height = img.size
    
    margin = int(2 / 2.54 * 96)  # aproximadamente 75 pixels
    
    if alignment == "Esquerda":
        x = margin
    elif alignment == "Direita":
        x = width - text_width - margin
    else:
        available_width = width - 2 * margin
        x = margin + (available_width - text_width) / 2
    
    y = height - text_height - margin
    
    if do_outline and outline_range > 0:
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                draw.text((x + dx, y + dy), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill=fill_color)
    return img

def generate_pdf(images):
    """Gera um PDF com base em uma lista de objetos PIL.Image."""
    pdf_bytes = io.BytesIO()
    if images:
        images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=images[1:])
    pdf_bytes.seek(0)
    return pdf_bytes


def scale_and_crop_to_fill(img, target_w, target_h):
    """
    Redimensiona e recorta a imagem para preencher completamente uma área de target_w x target_h,
    mantendo a proporção – semelhante à propriedade CSS 'cover'.
    """
    w, h = img.size
    ratio_img = w / h
    ratio_target = target_w / target_h

    if ratio_img > ratio_target:
        new_height = target_h
        scale = new_height / h
        new_width = int(w * scale)
        resized = img.resize((new_width, new_height), resample=Image.LANCZOS)
        left = (new_width - target_w) // 2
        final_img = resized.crop((left, 0, left + target_w, new_height))
    else:
        new_width = target_w
        scale = new_width / w
        new_height = int(h * scale)
        resized = img.resize((new_width, new_height), resample=Image.LANCZOS)
        top = (new_height - target_h) // 2
        final_img = resized.crop((0, top, new_width, top + target_h))
    return final_img

def generate_pdf_sangria(images, dpi=300):
    """
    Gera um PDF onde cada página tem exatamente 6.125" x 9.25" (aproximadamente 1838 x 2775 pixels a 300 dpi).
    Cada imagem é redimensionada e recortada para preencher completamente a página (estilo 'cover'),
    sem deixar margens em branco.
    """
    width_inch = 6.125
    height_inch = 9.25
    target_w = int(round(width_inch * dpi))   # Aproximadamente 1838 pixels
    target_h = int(round(height_inch * dpi))    # Aproximadamente 2775 pixels

    pdf_pages = []
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        filled_img = scale_and_crop_to_fill(img, target_w, target_h)
        pdf_pages.append(filled_img)

    pdf_bytes = io.BytesIO()
    if pdf_pages:
        pdf_pages[0].save(pdf_bytes, format="PDF", resolution=dpi, save_all=True, append_images=pdf_pages[1:])
    pdf_bytes.seek(0)
    return pdf_bytes

def generate_epub(files, start_page, end_page, initial_number, alignment, number_style, custom_color=None, add_numbering=True):
    """
    Gera um EPUB com numeração em rodapé para as páginas cujo número esteja entre start_page e end_page.
    Se add_numbering for False, não será adicionada numeração no EPUB.
    """
    book = epub.EpubBook()
    book.set_identifier("id_livro_123")
    book.set_title("Livro Ilustrado")
    book.set_language("pt")
    book.add_author("Globaltec")
    
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
    
        if add_numbering and start_page <= page_position <= end_page:
            display_number = initial_number + (page_position - start_page)
            display_text = int_to_roman(display_number) if number_style == "Romano" else str(display_number)
            html_color = html_colors.get(number_style, "#FFFFFF")
            if alignment == "Esquerda":
                align_style = "text-align:left; margin-left:75px;"
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
    
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters
    
    epub_bytes = io.BytesIO()
    epub.write_epub(epub_bytes, book)
    epub_bytes.seek(0)
    return epub_bytes

def move_page(file_index, new_position):
    """Move a página para a nova posição, ajustando st.session_state.order."""
    order = st.session_state.order
    current_pos = order.index(file_index)
    order.pop(current_pos)
    new_index = max(0, min(new_position - 1, len(order)))
    order.insert(new_index, file_index)
    st.session_state.order = order
    st.rerun()

def chunk_list(seq, chunk_size=7):
    """Divide a lista em sub-listas de tamanho chunk_size."""
    for i in range(0, len(seq), chunk_size):
        yield seq[i:i + chunk_size]

def book_page():
    # Inicializa a flag se ainda não existir
    if "book_generated" not in st.session_state:
        st.session_state.book_generated = False
    if "zip_data" in st.session_state and not st.session_state.book_generated:
        # Caso exista um ZIP da execução anterior, limpe-o
        del st.session_state.zip_data
        del st.session_state.zip_filename

    # Exibe a logo centralizada, se disponível
    logo_base64 = get_base64_image("logo.png")
    if logo_base64:
        st.markdown(f"""
            <div style="text-align:center;">
                <img src="data:image/png;base64,{logo_base64}" style="width:230px; margin-bottom:-10px;" />
            </div>
        """, unsafe_allow_html=True)
    
    st.title("Projeto Thoth - Geração de Livros")
    st.write("""
    Selecione as imagens do livro. Você pode selecionar uma ou várias páginas.
    Para cada página, insira a posição desejada e clique em **Atualizar posição** para reordenar.
    Se uma página for inserida em uma posição já ocupada, as outras serão deslocadas.
    
    Em seguida, defina:
      - O título do livro, que será o nome do arquivo zipado a ser baixado ou enviado ao Drive;
      - O intervalo de numeração;
      - O número inicial da numeração;
      - O estilo, o alinhamento e a cor da numeração.
    
    Clique em **Gerar Livro** para produzir:\n
      - Um PDF padrão; \n
      - Um PDF com "sangria" (imagem que preenche 100% da página, sem margens);\n
      - Um EPUB para publicações digitais;\n
      - Todos empacotados em um arquivo ZIP.
    """)
    
    uploaded_files = st.file_uploader("Escolha as imagens", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    
    if uploaded_files:
        if 'file_data' not in st.session_state:
            st.session_state.file_data = []
            st.session_state.order = []
        
        # Remove arquivos que não foram enviados novamente
        uploaded_names = {f.name for f in uploaded_files}
        indices_to_remove = [
            i for i, f in enumerate(st.session_state.file_data)
            if f["name"] not in uploaded_names
        ]
        for i in sorted(indices_to_remove, reverse=True):
            del st.session_state.file_data[i]
            st.session_state.order.remove(i)
            st.session_state.order = [idx - 1 if idx > i else idx for idx in st.session_state.order]
        
        # Adiciona novos arquivos que ainda não estavam na sessão
        existing_names = {f["name"] for f in st.session_state.file_data}
        new_files = [f for f in uploaded_files if f.name not in existing_names]
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
                new_pos = col.number_input("Posição", min_value=1, max_value=len(order), value=current_position, key=f"pos_{file_index}")
                if col.button("Atualizar posição", key=f"update_{file_index}"):
                    move_page(file_index, new_pos)
        
        st.write("### Defina o título do Livro")
        book_name = st.text_input("Digite o nome do livro:", value="MeuLivro")
        num_pages = len(order)
        st.write("### Defina a numeração")
        num_start = st.number_input("Início da numeração (posição)", min_value=1, max_value=num_pages, value=1, key="num_start")
        num_end = st.number_input("Última página a ser numerada (posição)", min_value=1, max_value=num_pages, value=num_pages, key="num_end")
        if num_start > num_end:
            st.error("O início não pode ser maior que o fim.")
        initial_number = st.number_input("Número inicial", min_value=1, value=1, key="initial_number")
        number_styles = ["Padrão", "Romano", "Fresco", "Moderno", "Vintage", "Elegante"]
        number_style = st.selectbox("Estilo de numeração", number_styles, index=0)
        
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
            st.markdown(f"""
                <div style="text-align:center;">
                    <img src="data:image/png;base64,{thumb_base64}" style="width:100px;" />
                </div>
            """, unsafe_allow_html=True)
        
        custom_color = st.color_picker("Escolha a cor para a numeração", value="#FFFFFF")
        alignment = st.selectbox("Alinhamento da numeração", ["Esquerda", "Central", "Direita"], index=1)
        
        # Opção para incluir numeração no EPUB
        include_epub_numbering = st.checkbox("Incluir numeração no EPUB", value=True)
    
        if st.button("Gerar Livro"):
            new_order = st.session_state.order
            image_list = []
            for pos, file_index in enumerate(new_order, start=1):
                f_dict = st.session_state.file_data[file_index]
                img = Image.open(io.BytesIO(f_dict["data"]))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                if num_start <= pos <= num_end:
                    display_number = initial_number + (pos - num_start)
                    img = add_page_number(img, display_number, alignment, style=number_style, custom_color=custom_color)
                image_list.append(img)
            
            # Gera os arquivos:
            pdf_bytes = generate_pdf(image_list)
            sangria_pdf_bytes = generate_pdf_sangria(image_list, dpi=300)
            reordered_files = [st.session_state.file_data[i] for i in new_order]
            epub_bytes = generate_epub(
                reordered_files,
                num_start,
                num_end,
                initial_number,
                alignment,
                number_style,
                custom_color=custom_color,
                add_numbering=include_epub_numbering
            )
            
            # Define os nomes dos arquivos com base no nome do livro
            pdf_filename = f"{book_name}.pdf"
            sangria_pdf_filename = f"{book_name}_sangria.pdf"
            epub_filename = "livro.epub"
            zip_filename = f"{book_name}.zip"
            
            # Empacota todos os arquivos em um ZIP
            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, mode="w") as zipf:
                zipf.writestr(pdf_filename, pdf_bytes.getvalue())
                zipf.writestr(sangria_pdf_filename, sangria_pdf_bytes.getvalue())
                zipf.writestr(epub_filename, epub_bytes.getvalue())
            zip_bytes.seek(0)
            
            # Armazena os dados do ZIP e o nome no st.session_state
            st.session_state.zip_data = zip_bytes.getvalue()
            st.session_state.zip_filename = zip_filename
            st.session_state.book_generated = True
            
            st.success("Livro gerado com sucesso!")
            st.download_button("Baixar ZIP", data=zip_bytes, file_name=zip_filename, mime="application/zip")
    
    # Exibe o botão de Enviar para o Google Drive somente se o livro foi gerado
    if st.session_state.get("book_generated", False):
        if st.button("Enviar para o Google Drive"):
            folder_id = "1aOIGtkAVjfh5qfxWidgbR-yLp0C4ZzjG"  # Substitua pelo ID real da pasta
            file_id = upload_to_drive(st.session_state.zip_data, st.session_state.zip_filename, folder_id=folder_id)
            drive_link = f"https://drive.google.com/file/d/{file_id}/view"
            st.success(f"Arquivo enviado com sucesso! Nome do arquivo: {book_name}")
            st.markdown(f"✅ [Clique aqui para acessar o arquivo no Google Drive]({drive_link})")

if __name__ == "__main__":
    book_page()
