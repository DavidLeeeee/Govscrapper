from enum import Enum

class ScrapeTarget(Enum):
    # 통합 지원사업 포털
    # BIZINFO = ("bizinfo", "https://www.bizinfo.go.kr", "기업마당") # API형태로 제공. -> https://www.bizinfo.go.kr/apiList.do, 분류가 너무 포괄적임
    # KSTARTUP = ("kstartup", "https://www.k-startup.go.kr", "K-Startup") # Startup 대상

    SMES = ("smes", "https://www.smes.go.kr", "중소벤처24") # 제일 유용해보인다.

    # 국가 R&D / 과제 공고
    IRIS = ("iris", "https://www.iris.go.kr", "IRIS 범부처통합연구지원시스템") # https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do
    NTIS = ("ntis", "https://www.ntis.go.kr", "NTIS 국가R&D통합공고") # 개인정보보호위원회, 과학기술정보통신부 한정
    # SMTECH = ("smtech", "https://www.smtech.go.kr", "SMTECH 중소기업기술개발사업") # 대상은 아닌듯 하다

    # SW / AI / ICT 전문기관
    # KOSA = ("kosa", "https://www.sw.or.kr", "KOSA 정부지원사업")
    # NIPA = ("nipa", "https://www.nipa.kr", "정보통신산업진흥원")
    IITP = ("iitp", "https://www.iitp.kr", "정보통신기획평가원") # 용역 중심, 나라장터: https://www.g2b.go.kr/link/FIUA006_01/single/?untySrchSeCd=BD&rowCnt=&instCd=D557091&demaInstNm=&hghrkInstCd=&prcmBsneAreaCd=%EC%A0%84%EC%B2%B4+%EC%A1%B0070001+%EC%A1%B0070002+%EC%A1%B0070003+%EC%A1%B0070004+%EC%A1%B0070005&prcmMthoSeCd=&frcpYn=N&laseYn=N&rsrvYn=N&chkInstCd=&urlSrchSeCd=instCd&demaInstCd=IN0100000093769&prcmMaagSeCd=
    NIA = ("nia", "https://www.nia.or.kr", "한국지능정보사회진흥원") # 크롤링하기 불편한 -완전 자율 형태-의 글... 인데 유용한 공고 있어보이기도 함
    # KDATA = ("kdata", "https://www.kdata.or.kr", "한국데이터산업진흥원") # 별 내용 없어보임
    KISA = ("kisa", "https://www.kisa.or.kr", "한국인터넷진흥원") # 가장 정보보호 관련 공고와 유사함
    KISA_BID = ("kisa_bid", "https://www.kisa.or.kr/403", "KISA 입찰공고")
    # KISIA = ("kisia", "https://www.ksecurity.or.kr", "정보보호산업진흥포털") # 공고관련 글은 안보임

    # 산업기술 / 기술사업화
    # KEIT = ("keit", "https://www.keit.re.kr", "한국산업기술기획평가원") # 애매하다...
    # KIAT = ("kiat", "https://www.kiat.or.kr", "한국산업기술진흥원") # 애매하다....
    KPASS = ("kpass", "https://www.k-pass.kr", "K-PASS") # 애매하다...

    # 수출 / IP / 디자인 -> 기타 공고... 세부적으로 볼 필요는 없고 키워드기반으로만 특정 요소만 검색한다.
    EXPORTVOUCHER = ("exportvoucher", "https://www.exportvoucher.com", "수출바우처")
    KOTRA = ("kotra", "https://www.kotra.or.kr", "KOTRA")
    KITA = ("kita", "https://www.kita.net", "한국무역협회")
    KISTA = ("kista", "https://www.kista.re.kr", "한국특허전략개발원")
    KIPA = ("kipa", "https://www.kipa.org", "한국발명진흥회")
    KIDP = ("kidp", "https://www.kidp.or.kr", "한국디자인진흥원")

    # 지역 - 서울/경기 IT 기업 기준
    SEOUL_RND = ("seoul_rnd", "https://seoul.rnbd.kr", "서울R&D지원센터") # 좋아보인다
    SBA = ("sba", "https://www.sba.seoul.kr", "서울경제진흥원")
    EGBIZ = ("egbiz", "https://www.egbiz.or.kr", "경기기업비서 이지비즈")
    GBSA = ("gbsa", "https://www.gbsa.or.kr", "경기도경제과학진흥원")

    def __init__(self, source_name: str, base_url: str,
    display_name: str):
        self.source_name = source_name
        self.base_url = base_url
        self.display_name = display_name
