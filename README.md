# BibTeX Cleaner & Converter

Last update: Jan 21 2025

Made by [홍성민](https://smhongok.github.io)

이 프로젝트는 BibTeX 파일을 읽어서, 특정 머신러닝/컴퓨터비전 학회(\@inproceedings) 엔트리를 \@article 형태로 자동 변환하거나(또는 그대로 두기도 가능), 제목에서 대문자 약어를 보존하는 등의 **일괄 정리**를 수행합니다. 또한 **주석**, **@String 매크로**, **파일 내 순서**를 최대한 그대로 유지하면서, 원하는 **필드 정리**를 자동으로 적용합니다.

## 주요 특징

1. **학회 감지 & 변환**  
   - 주요 학회(\[NeurIPS, ICML, ICLR, CVPR, ICCV, ECCV, ACL, …\])가 감지되면,  
     - (기본) `@inproceedings → @article + journal={학회 약어}`  
     - `volume`, `pages`, `publisher` 등 자잘한 필드 제거  
   - `--keep-inproceedings` 옵션을 주면 `@inproceedings` 형태를 유지하되, `booktitle={학회 약어}`로만 바꾸고, 마찬가지로 여분 필드를 제거

2. **제목 내 대문자 보존**  
   - “맨 앞 단어 + 콜론” → `{단어}:`로 감싸기 (예: `SalUn: ...` → `"{SalUn}: ..."`)  
   - 2글자 이상의 **연속된 대문자**는 `{{...}}`로 감싸 TeX 컴파일 시 대문자가 소문자로 바뀌지 않도록 함 (예: `GAN` → `{{GAN}}`)

3. **@String 매크로 / 주석 / 순서 유지**  
   - 일반적으로 `bibtexparser`는 엔트리만 파싱해 주석/매크로/줄 순서를 잃기 쉬운데,  
   - 이 프로젝트는 **원본 `.bib`를 라인 단위로 파싱**하며, 수정할 엔트리만 `bibtexparser` 결과로 치환 → **나머지는 그대로** 유지.

4. **명령줄 인터페이스**  
   - `--input`, `--output`: 입력/출력 파일 지정  
   - `--keep-inproceedings`: 학회 엔트리를 `@article`로 바꾸지 않고 그대로 두기

## 설치 방법

### 1. 의존 라이브러리

- Python 3.7+ (혹은 그 이상)  
- `bibtexparser` (버전 1.2 이상)  
- `argparse` (표준 라이브러리), `re`, `sys` (표준 라이브러리)

아래처럼 pip를 통해 설치할 수 있습니다:
```bash
pip install bibtexparser
```
(또는 `pip install -r requirements.txt` 파일을 만들어 관리해도 좋습니다.)

### 2. 코드 다운로드

이 리포지토리를 클론하거나 ZIP으로 다운로드하여, `main.py`(또는 `bibcleaner.py`) 파일이 있는 위치로 이동합니다.

```bash
git clone https://github.com/smhongok/bibTeX-cleaner.git
cd bib-cleaner
```

### 3. 실행 예시

아래는 가장 간단한 실행 예시입니다.

```bash
# 기본적으로 @inproceedings → @article로 변환
python main.py --input input.bib --output output.bib
```

- `input.bib`: 정리할 BibTeX 파일  
- `output.bib`: 정리된 결과를 저장할 파일 이름

만약 학회 항목을 `@inproceedings`로 **그대로** 두고 싶다면:

```bash
python main.py --keep-inproceedings --input input.bib --output output.bib
```

## 사용 흐름

1. **BibTeX 파일 파싱**  
   - `bibtexparser`를 이용해 주요 **엔트리**(\@article, \@inproceedings 등)를 메모리에 로드  
   - 동시에 파일 원본 전체를 라인 단위로 읽어 **주석**, `@String(...)`, 공백 라인을 캐치

2. **엔트리 수정** (`process_bibtex_entries`)  
   - “주요 학회(\[NeurIPS, ICML, ICLR 등\])” 감지 시, `@inproceedings -> @article` or 유지  
   - `volume`, `pages`, `month` 등의 필드 제거  
   - `title`에서 **대문자 약어** 보호 (이중 중괄호로 감싸기)

3. **결과 병합**  
   - 수정된 엔트리는 새로 덤프  
   - 원본의 **주석, @String, 순서, 공백** 그대로 출력 (수정된 엔트리만 치환)

## 커스텀

- **학회 목록**: `CONFERENCE_MAP` 딕셔너리를 확장/수정하면 됩니다.  
- **제거 필드**: `FIELDS_TO_REMOVE` 리스트를 수정  
- **제목 처리 로직**: `preserve_uppercase_acronyms()` 함수에서 정규식을 바꾸거나, 특정 단어만 처리하도록 하는 등 마음껏 조정 가능

## 알려진 이슈

- BibTeX에 중괄호가 매우 복잡하게 중첩된 경우(매크로/특수문자)에서, 주석/엔트리 파싱이 제대로 안 될 가능성 있음  
- `bibtexparser`가 처리하지 못할 정도의 비표준 포맷은 지원이 어려움

## 라이선스

- (선택) MIT License, Apache License 2.0 등 원하는 라이선스 문구를 넣으시면 됩니다.

## 기여

- 버그 리포트나 PR(풀 리퀘스트) 환영합니다.  
- 새 학회 추가, 고급 규칙(예: 문장 전체 대문자 필터) 등도 자유롭게 건의하세요!
