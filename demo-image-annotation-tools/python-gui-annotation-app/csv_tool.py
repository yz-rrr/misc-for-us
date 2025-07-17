import os
import csv


class CSVTool():
    def __init__(self):
        pass

    def detect_bom(self, filename):
        start = b''
        with open(filename, 'rb') as f:
            start = f.read(4)  # UTF-8 BOMは3バイト、UTF-16/32はそれ以下またはそれ以上のバイト
        # UTF-8 BOM
        if start.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        # UTF-16 LE BOM
        if start.startswith(b'\xff\xfe') and not start.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-16'
        # UTF-16 BE BOM
        if start.startswith(b'\xfe\xff'):
            return 'utf-16'
        # UTF-32 LE BOM
        if start.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32'
        # UTF-32 BE BOM
        if start.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32'
        return None

    def try_decode(self, data, encoding):
        try:
            data.decode(encoding, errors='strict')
            return True
        except UnicodeDecodeError:
            return False

    def detect_file_encoding(self, filename):

        # １．BOMチェックで判定できる場合はそのエンコードを採用する
        bom_encoding = self.detect_bom(filename)
        if bom_encoding:
            return bom_encoding

        # ２．候補エンコードを用いて実際にデコードできるかを試す
        # 候補には、utf-8、shift_jis、euc_jp、iso2022_jpなどを含めています
        candidates = ['utf-8', 'shift_jis', 'euc_jp', 'iso2022_jp']
        with open(filename, 'rb') as f:
            data = f.read()

        valid_encodings = [enc for enc in candidates if self.try_decode(data, enc)]
        
        # 複数の候補が存在する場合は、優先順位順に返す（ここでは候補リスト順）
        if valid_encodings:
            return valid_encodings[0]

        # どれにもデコードできなかった場合、デフォルトとしてutf-8を返す
        return 'utf-8'


