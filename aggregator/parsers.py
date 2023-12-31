
import itertools
import sys

def file_to_pdf(file_path, parser_name):
    return getattr(sys.modules[__name__], "file_to_pdf_%s" % parser_name)(file_path)

def file_to_pdf_tika(file_path):
    import tika.parser
    pdf = tika.parser.from_file(file_path)
    pdf_contents = pdf['content']
    return pdf_contents

def file_to_pdf_miner_text(file_path):
    import io
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.pdfpage import PDFPage
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams

    from pdfminer.converter import PDFPageAggregator
    from pdfminer.layout import LTPage, LTChar, LTAnno, LAParams, LTTextBox, LTTextLine

    fp = open(file_path, 'rb')
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr,
                           # codec=codec,
                           laparams=laparams)
    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # Process each page contained in the document.

    for page in PDFPage.get_pages(fp):
        interpreter.process_page(page)
        data =  retstr.getvalue()
        try: # may fail for obscure reasons
            device.get_result()
        except:
            pass

    return data

def file_to_pdf_miner_aggregate(file_path, merge = True):
    import io
    from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
    from pdfminer.pdfpage import PDFPage
    from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
    from pdfminer.layout import LAParams

    from pdfminer.converter import PDFPageAggregator
    from pdfminer.layout import LTPage, LTChar, LTAnno, LAParams, LTTextBox, LTTextLine

    class PDFPageDetailedAggregator(PDFPageAggregator):
        def __init__(self, rsrcmgr, pageno=1, laparams=None):
            PDFPageAggregator.__init__(self, rsrcmgr, pageno=pageno, laparams=laparams)
            self.rows = []
            self.page_number = 0
        def receive_layout(self, ltpage):        
            def render(item, page_number):
                if isinstance(item, LTPage) or isinstance(item, LTTextBox):
                    for child in item:
                        render(child, page_number)
                elif isinstance(item, LTTextLine):
                    child_str = ''
                    for child in item:
                        if isinstance(child, (LTChar, LTAnno)):
                            child_str += child.get_text()
                    child_str = ' '.join(child_str.split()).strip()
                    if child_str:
                        row = (page_number, item.bbox[0], item.bbox[1], item.bbox[2], item.bbox[3], child_str) # bbox == (x1, y1, x2, y2)
                        self.rows.append(row)
                    for child in item:
                        render(child, page_number)
                return
            render(ltpage, self.page_number)
            self.page_number += 1
            self.rows = sorted(self.rows, key = lambda x: (x[0], -int(x[2]), x[1]))
            self.result = ltpage


    fp = open(file_path, 'rb')
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    device = PDFPageDetailedAggregator(rsrcmgr,
                           laparams=laparams)

    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    mergeDistance = 3
    rows = ""
    # Process each page contained in the document.
    for page in PDFPage.get_pages(fp):
        interpreter.process_page(page)
        device.get_result()

    previousBottomY = 0
    previousPage = -1
    previousRow = [] # [[], [], []]
    for bottomY, r in itertools.groupby(device.rows, key = lambda x: int(x[2])):
        # Convert iterator of tuples into array of array
        row = [list(item) for item in r]
        # row is: (page, leftX, bottomY, rightX, topY, text)
        page = row[0][0]
        topY = row[0][4]
        # valuesInRow = [item[5] for item in row]
        # rows += '\t'.join(valuesInRow) + '\n'
        # print(topY, previousBottomY, row)
        if page == previousPage and topY > previousBottomY - mergeDistance:
            # merge rows
            #print('Merge row ', topY, row, 'with', previousRow)
            for item in row:
                found = False
                for pItem in previousRow:
                    if pItem[3] >= item[1] and pItem[1] <= item[3]:
                        pItem[5] += ' ' + item[5]
                        pItem[1] = min(item[1], pItem[1]) # left
                        pItem[2] = min(item[2], pItem[2]) # bottom
                        pItem[3] = max(item[3], pItem[3]) # right
                        pItem[4] = max(item[4], pItem[4]) # top
                        found = True
                        break
                if not found:
                    previousRow.append(item)
                    previousRow = sorted(previousRow, key= lambda item: item[1])
        else:
            # no merge, commit previous row
            if previousRow:
                valuesInRow = [item[5] for item in previousRow]
                rows += '\t'.join(valuesInRow) + '\n'
            # create a new row but do not commit it yet
            previousRow = row
        previousBottomY = min(previousRow, key=lambda item:item[2])[2]
        previousPage = page
    #print(rows)
    valuesInRow = [item[5] for item in previousRow]
    rows += '\t'.join(valuesInRow) + '\n'
    data = rows

    return data

def file_to_pdf_pdfplumber(file_path):
    import pdfplumber
    data = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            data += page.extract_text()
    return data
