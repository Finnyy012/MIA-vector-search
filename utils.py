import requests
import os
from bs4 import BeautifulSoup
import spacy
from tqdm import tqdm
from urllib.parse import urlparse, urljoin

def fetch_webpage(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()

def unchunk_from_node(metadata):
    text = fetch_webpage(metadata["url"])
    return text[metadata["chunk_start"]:metadata["chunk_end"]]

def index_whitespace(text, substring):
    text_chars = []
    text_indices = []
    for i, c in enumerate(text):
        if not c.isspace():
            text_chars.append(c)
            text_indices.append(i)
    
    stripped_sub = ''.join(substring.split())
    
    if not stripped_sub:
        if not substring:
            raise ValueError("substring is empty")
        first_char = substring[0]
        for i, c in enumerate(text):
            if c == first_char:
                return i
        raise ValueError("substring not found")
    
    pattern = list(stripped_sub)
    pattern_len = len(pattern)
    lps = [0] * pattern_len
    length = 0  
    
    for i in range(1, pattern_len):
        while length > 0 and pattern[i] != pattern[length]:
            length = lps[length - 1]
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
        else:
            lps[i] = 0
    
    j = 0 
    for i in range(len(text_chars)):
        while j > 0 and text_chars[i] != pattern[j]:
            j = lps[j - 1]
        if text_chars[i] == pattern[j]:
            j += 1
            if j == pattern_len:
                start_in_chars = i - pattern_len + 1
                return text_indices[start_in_chars]
    
    raise ValueError("substring not found")

def chunk_text(nlp: spacy.Language, text: str, max_tokens: int = 512, overlap: int = 10):
    # source: https://www.reddit.com/r/OpenAI/comments/15wayu9/comment/jx14ovn/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button
    doc = nlp(text)
    sentences = [sent.text for sent in doc.sents]
    indices = []
    chunks = []
    current_chunk = []
    current_token_count = 0

    for sentence in (sentences):
        sentence_doc = nlp(sentence)
        sentence_tokens = [token.text for token in sentence_doc]
        num_tokens_in_sentence = len(sentence_tokens)
        
        if num_tokens_in_sentence > max_tokens:
            start = 0
            end = max_tokens
            while start < num_tokens_in_sentence:
                chunk = " ".join(sentence_tokens[start:end])
                chunks.append(chunk)
                ind = index_whitespace(text, chunk)
                ind2 = len(text)-index_whitespace(text[::-1], chunk[::-1])
                indices.append((ind, ind2))
                start += max_tokens - overlap
                end = min(start + max_tokens, num_tokens_in_sentence)
            current_chunk = []
            current_token_count = 0
            continue

        if current_token_count + num_tokens_in_sentence > max_tokens:
            chunk = " ".join(current_chunk)
            chunks.append(chunk)
            ind = index_whitespace(text, chunk)
            ind2 = len(text)-index_whitespace(text[::-1], chunk[::-1])
            indices.append((ind, ind2))
            current_chunk = []
            current_token_count = 0

        current_chunk.append(sentence)
        current_token_count += num_tokens_in_sentence

    if current_chunk:
        chunk = " ".join(current_chunk)
        chunks.append(chunk)
        ind = index_whitespace(text, chunk)
        ind2 = len(text)-index_whitespace(text[::-1], chunk[::-1])
        indices.append((ind, ind2))
    return chunks, indices


def find_sub_urls(base_url):
    try:
        response = requests.get(base_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []

    final_url = response.url
    parsed_base = urlparse(final_url)
    base_path = parsed_base.path

    if not base_path.endswith('/'):
        base_path += '/'

    soup = BeautifulSoup(response.text, 'html.parser')
    sub_urls = set()
    non_page_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', 
                          '.docx', '.zip', '.mp3', '.mp4', '.css', '.js'}

    for link in (pbar := tqdm(soup.find_all('a', href=True))):
        pbar.set_description(f"Fetching urls")
        href = link['href']
        absolute_url = urljoin(final_url, href)
        parsed_absolute = urlparse(absolute_url)

        if parsed_absolute.scheme != parsed_base.scheme:
            continue
        if parsed_absolute.netloc != parsed_base.netloc:
            continue

        if not parsed_absolute.path.startswith(base_path):
            continue

        path = parsed_absolute.path
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1].lower()
        if ext in non_page_extensions:
            continue

        parsed_absolute = parsed_absolute._replace(fragment='')
        clean_url = parsed_absolute.geturl()

        sub_urls.add(clean_url)

    sub_urls.add(base_url)

    return sorted(sub_urls)
