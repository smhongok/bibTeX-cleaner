import re
import sys
import argparse
import bibtexparser

#####################################################################
# 1. 설정: 학회 매핑, 제거할 필드, etc.
#####################################################################

CONFERENCE_MAP = {
    'NeurIPS': [
        'NeurIPS',
        'Advances in Neural Information Processing Systems',
        'Conference on Neural Information Processing Systems',
        'Neural Information Processing Systems'
    ],
    'ICML': [
        'ICML',
        'International Conference on Machine Learning'
    ],
    'ICLR': [
        'ICLR',
        'International Conference on Learning Representations'
    ],
    'CVPR': [
        'CVPR',
        'IEEE Conference on Computer Vision and Pattern Recognition',
        'Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition',
        'IEEE/CVF Conference on Computer Vision and Pattern Recognition'
    ],
    'ICCV': [
        'ICCV',
        'IEEE International Conference on Computer Vision'
    ],
    'ECCV': [
        'ECCV',
        'European Conference on Computer Vision'
    ],
    'ACL': [
        'ACL',
        'Annual Meeting of the Association for Computational Linguistics'
    ],
    'WACV': [
        'WACV',
        'IEEE Winter Conference on Applications of Computer Vision'
    ],
    'AAAI': [
        'AAAI',
        'Association for the Advancement of Artificial Intelligence'
    ],
    # 필요하다면 여기 계속 확장
}

FIELDS_TO_REMOVE = ['volume', 'number', 'pages', 'month', 'publisher', 'organization']

#####################################################################
# 2. 문자열(학회) 감지 함수
#####################################################################
def detect_conference(booktitle_or_journal):
    """
    booktitle(또는 journal)에서 CONFERENCE_MAP 중 어느 것에 해당하는지 탐색.
    해당하면 그 학회의 약어(abbr)를 반환, 아니면 None.
    """
    if not booktitle_or_journal:
        return None
    
    lower_str = booktitle_or_journal.lower()
    for abbr, patterns in CONFERENCE_MAP.items():
        for p in patterns:
            if p.lower() in lower_str:
                return abbr
    return None

#####################################################################
# 3. 제목에서 대문자/맨앞단어 처리
#####################################################################
def preserve_uppercase_acronyms(title):
    """
    1) 맨 앞 "단어:"를 {단어}: 로 감싸기
    2) 2글자 이상 연속된 대문자 약어는 {{...}}로 감싸기
    """
    if not title:
        return title

    # 1) 맨 앞 "단어:" 감싸기
    def wrap_token_before_colon(match):
        word = match.group(1)
        if word.startswith('{') and word.endswith('}'):
            return match.group(0)  # 이미 { } 로 감싸져있으면 그대로
        return f"{{{word}}}:"

    title_new = re.sub(r"^([^\s:]+):", wrap_token_before_colon, title, count=1)

    # 2) 2글자 이상 연속된 대문자
    def replace_acronym(m):
        acronym = m.group(0)
        if acronym.startswith('{') and acronym.endswith('}'):
            return acronym  # 이미 감싸져있으면 그대로
        return "{" + acronym + "}"

    title_new = re.sub(r"\b[A-Z]{2,}\b", replace_acronym, title_new)
    return title_new

#####################################################################
# 4. bibtexparser로 읽어온 Entries 변환 로직
#####################################################################
def process_bibtex_entries(bib_database, keep_inproceedings):
    """
    - 각 entry를 순회하며:
      1) title 대문자 약어 처리
      2) inproceedings + 학회 감지 → article (혹은 그대로 inproceedings) + journal(or booktitle)=학회약어
      3) 불필요 필드 제거
    """
    for entry in bib_database.entries:
        # entry['ID'] = citation key
        entry_type = entry.get('ENTRYTYPE', '').lower()

        # (1) title
        if 'title' in entry:
            old_title = entry['title']
            new_title = preserve_uppercase_acronyms(old_title)
            if new_title != old_title:
                print(f"[TITLE] {entry['ID']}: '{old_title}' -> '{new_title}'")
                entry['title'] = new_title

        # (2) inproceedings 처리
        if entry_type == 'inproceedings':
            conf_abbr = detect_conference(entry.get('booktitle', ''))
            if conf_abbr:
                if keep_inproceedings:
                    # 그대로 inproceedings 유지, 대신 booktitle=학회약어로
                    old_bt = entry.get('booktitle', '')
                    entry['booktitle'] = conf_abbr
                    print(f"[TYPE] {entry['ID']}: keep @inproceedings, booktitle='{old_bt}' -> '{conf_abbr}'")
                else:
                    # @article 로 전환
                    old_bt = entry.pop('booktitle', None)
                    entry['ENTRYTYPE'] = 'article'
                    entry['journal'] = conf_abbr
                    print(f"[TYPE] {entry['ID']}: @inproceedings -> @article, removed booktitle='{old_bt}', set journal='{conf_abbr}'")

                # 불필요 필드 제거
                for f in FIELDS_TO_REMOVE:
                    if f in entry:
                        removed_val = entry.pop(f)
                        print(f"   removed field '{f}'='{removed_val}'")

        # (3) 이미 article인 경우도, 학회면 volume/pages 등 제거
        elif entry_type == 'article':
            conf_abbr = detect_conference(entry.get('journal', ''))
            if conf_abbr:
                # 불필요 필드 제거
                for f in FIELDS_TO_REMOVE:
                    if f in entry:
                        removed_val = entry.pop(f)
                        print(f"[ARTICLE CLEANUP] {entry['ID']}: removed '{f}'='{removed_val}'")
                if not keep_inproceedings:
                    # 그대로 article 유지, 대신 booktitle=학회약어로
                    old_bt = entry.get('journal', '')
                    entry['journal'] = conf_abbr
                    print(f"[TYPE] {entry['ID']}: keep @article, journal='{old_bt}' -> '{conf_abbr}'")
                else:
                    # @inproceedings 로 전환
                    old_bt = entry.pop('journal', None)
                    entry['ENTRYTYPE'] = 'inproceedings'
                    entry['booktitle'] = conf_abbr
                    print(f"[TYPE] {entry['ID']}: @article -> @inproceedings, removed journal='{old_bt}', set booktitle='{conf_abbr}'")
        # else: 다른 타입(misc, etc.)은 스킵

    return bib_database

#####################################################################
# 5. 원본 라인을 "그대로" 보존하기 위한 헬퍼
#    - bibtexparser는 기본적으로 주석, @string, whitespace, 순서를 보존하지 않음
#    - 아래 로직은 파일 전체를 line-by-line으로 읽어 블록을 구분
#      * @String(...), @SomeType{...} 블록을 찾아내서
#      * entry인 경우 수정된 bib_database에서 바뀐 버전으로 출력
#      * 그 외(매크로, 주석, 공백 등)는 그대로 출력
#####################################################################

def find_entry_key_and_type(first_line):
    """
    예: '@article{smith2020abc,' -> (entrytype='article', key='smith2020abc')
         '@inproceedings{kingma2014vae,' -> (entrytype='inproceedings', key='kingma2014vae')
    반환: (None, None) 이면 "이건 엔트리 시작 줄이 아님"
    """
    # 대략적으로 '@(entrytype){key,' 구조 파싱
    # @(\w+)\{([^,]+),
    pattern = r'^\s*@(\w+)\s*\{\s*([^,]+)\s*,'
    m = re.match(pattern, first_line.strip(), flags=re.IGNORECASE)
    if m:
        etype = m.group(1)   # article, inproceedings, etc.
        ekey  = m.group(2)   # smith2020abc
        return etype.lower(), ekey.strip()
    return None, None

def read_bib_blocks(lines):
    """
    Generator: line-by-line으로 순회하여 
    - @String(...) 단일 라인 (혹은 멀티라인) 매크로
    - @entry{...} 블록
    - 그 외 일반 라인(주석, 공백 등)
    를 구분해서 (block_type, raw_lines) 형태로 yield

    block_type:
      - 'string'  : @String(...) 매크로 전체
      - 'entry'   : @article{...}, @inproceedings{...}, ...
      - 'other'   : 주석, 공백, etc.
    """
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # 1) @String(...) 인지 확인
        #    BibTeX 상 @string(...) 은 한 줄에 모두 쓸 수도 있고, 여러 줄 걸칠 수도 있으나,
        #    여기서는 간단히 괄호 짝이 맞을 때까지 읽어들이는 식으로 처리
        if re.match(r'^\s*@string\s*\(', line.strip(), flags=re.IGNORECASE):
            # 매크로 블록 시작
            block_lines = [line]
            i += 1
            paren_count = line.count('(') - line.count(')')
            # 괄호가 모두 닫힐 때까지
            while i < n and paren_count > 0:
                block_lines.append(lines[i])
                paren_count += lines[i].count('(')
                paren_count -= lines[i].count(')')
                i += 1
            yield ('string', block_lines)
            continue

        # 2) @entry{...} 인지 확인
        etype, ekey = find_entry_key_and_type(line)
        if etype is not None and ekey is not None:
            # 엔트리 블록 시작
            block_lines = [line]
            i += 1
            brace_level = line.count('{') - line.count('}')
            while i < n and brace_level > 0:
                block_lines.append(lines[i])
                brace_level += lines[i].count('{')
                brace_level -= lines[i].count('}')
                i += 1
            yield ('entry', block_lines)
            continue

        # 그 외 일반 라인 (주석/공백/텍스트 등)
        yield ('other', [line])
        i += 1

def entry_to_bibtex_string(db, key):
    """
    bibtexparser로 수정된 db에서, key에 해당하는 entry를 찾아
    bibtexparser.dump_s() 로 단일 엔트리만 문자열로 만든 뒤 리턴.
    만약 db 내에 없으면 None 리턴.
    """
    # key 대소문자 구분 문제: bibtexparser는 기본적으로 동일 키라도 대소문자 상관없이 저장
    # 그러나 일반적으로 ID는 하나뿐이니 그냥 매칭
    for e in db.entries:
        if e.get('ID') == key:
            # 임시 db를 만들어서 그 entry만 dump
            temp_db = bibtexparser.bibdatabase.BibDatabase()
            temp_db.entries = [e]
            return bibtexparser.dumps(temp_db).strip()
    return None

#####################################################################
# 6. 메인 함수
#####################################################################
def main():
    parser = argparse.ArgumentParser(description='Process BibTeX files without losing comments, macros, or order.')
    parser.add_argument('--keep-inproceedings',
                        action='store_true',
                        help='If set, keep inproceedings type for known conferences (instead of converting to article).')
    parser.add_argument('--input', default='input.bib', help='Input BibTeX file name')
    parser.add_argument('--output', default='output.bib', help='Output BibTeX file name')
    args = parser.parse_args()

    # 1) 파일 전체를 한 번에 읽어서 lines로 보관
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{args.input}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {args.input}: {e}")
        sys.exit(1)

    # 2) bibtexparser로 파싱 (이때 주석, @string 등은 보존되지 않음 - 하지만 엔트리는 얻음)
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            bib_database = bibtexparser.load(f)
    except Exception as e:
        print(f"Error parsing {args.input} with bibtexparser: {e}")
        sys.exit(1)

    # 3) 엔트리 가공
    bib_database = process_bibtex_entries(bib_database, keep_inproceedings=args.keep_inproceedings)

    # 4) 원본 lines를 블록 단위로 읽으며, 엔트리는 업데이트된 버전으로 치환
    output_lines = []
    for block_type, block_lines in read_bib_blocks(lines):
        if block_type == 'string':
            # @String(...) 블록은 그대로
            output_lines.extend(block_lines)
        elif block_type == 'entry':
            # 엔트리인 경우, key 파싱
            first_line = block_lines[0]
            etype, ekey = find_entry_key_and_type(first_line)
            if etype and ekey:
                # 업데이트된 entry가 db에 있으면 치환
                updated_str = entry_to_bibtex_string(bib_database, ekey)
                if updated_str is not None:
                    # bibtexparser.dumps() 결과는 여러 줄일 수 있으므로 split
                    updated_lines = [ln + "\n" for ln in updated_str.splitlines()]
                    output_lines.extend(updated_lines)
                else:
                    # db에 없는 key면 원본 그대로
                    output_lines.extend(block_lines)
            else:
                # 혹시 파싱이 안 된다면 그냥 원본 출력
                output_lines.extend(block_lines)
        else:
            # 주석, 공백 등 other는 그대로
            output_lines.extend(block_lines)

    # 5) 결과 저장
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
        print(f"Done. Output written to {args.output}")
    except Exception as e:
        print(f"Error writing {args.output}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
