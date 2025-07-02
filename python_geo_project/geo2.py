import pandas as pd
import folium
import requests
import time
from folium import IFrame
import geopandas as gpd
from shapely.geometry import mapping

# 카카오 API 키 (KakaoAK 포함)
KAKAO_API_KEY = 'KakaoAK c3212f514f3790bd3ba99b4c9acf0298'

def geocode_kakao(address):
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": KAKAO_API_KEY}
    params = {'query': address}

    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"[HTTP {response.status_code}] Error for address: {address}")
            return None, None

        result = response.json()

        if 'documents' in result and result['documents']:
            lat = float(result['documents'][0]['y'])
            lon = float(result['documents'][0]['x'])
            return lat, lon
        
        else:
            return None, None
    except Exception as e:
        print(f"Error geocoding {address}: {e}")
        return None, None

# CSV 불러오기
df = pd.read_csv("market.csv", encoding='cp949')

jeju_markets = df[df['시도'] == '제주특별자치도'].copy()
jeju_markets = jeju_markets[['시장명', '도로명주소']].dropna()

# 온누리 상품권 가맹점 데이터 불러오기
onuri_df = pd.read_csv("onuri.csv", encoding='cp949')
onuri_df = onuri_df[['소재지', '가맹점명', '취급품목']].dropna()

# 유동인구, 카드 매출 데이터
pop_df = pd.read_csv("card.csv", encoding='cp949')
latest_month = pop_df['년월'].max()
pop_df = pop_df[pop_df['년월'] == latest_month]

# 위도/경도 추출
latitudes = []
longitudes = []

for address in jeju_markets['도로명주소']:
    lat, lon = geocode_kakao(address)
    latitudes.append(lat)
    longitudes.append(lon)
    time.sleep(0.5)  # API 과다 호출 방지

jeju_markets['위도'] = latitudes
jeju_markets['경도'] = longitudes

# Folium 지도 생성
m = folium.Map(location=[33.38, 126.55], zoom_start=10)

# shp 파일 불러오기
geo_df = "jeju_eupmyeondong.shp"
gdf = gpd.read_file(geo_df, encoding='cp949')

# 읍면동명 정제 함수
def clean_emd_nm(name):
    name = name.replace("일동", "1동")
    name = name.replace("이동", "2동")
    name = name.replace("삼동", "3동")
    name = name.replace("외도일동", "외도동")
    name = name.replace("외도이동", "외도동")
    name = name.replace("이호일동", "이호동")
    name = name.replace("이호이동", "이호동")
    name = name.replace("삼양일동", "삼양동")
    name = name.replace("이호이동", "이호동")
    return name

mapping_dict = {
    '삼양일동': '삼양동',
    '삼양이동': '삼양동',
    '삼양삼동': '삼양동',
    '오라일동': '오라동',
    '오라이동': '오라동',
    '오라삼동': '오라동',
    '화북일동': '화북동',
    '화북이동': '화북동',
    '용담일동': '용담1동',
    '용담삼동': '용담3동',
    '용담이동': '용담2동',
    '외도일동': '외도동',
    '외도이동': '외도동',
    '도두일동': '도두동',
    '도두이동': '도두동',
    '일도이동': '일도2동',
    '일도일동': '일도1동',
    '이호일동': '이호동',
    '이호이동': '이호동',
    '아라일동': '아라동',
    '아라이동': '아라동',
    '삼도이동': '삼도2동',
    '삼도일동': '삼도1동',
    '이도일동': '이도1동',
    '이도이동': '이도2동',
    '일도일동': '일도1동',
}
gdf['EMD_NM_정제'] = gdf['EMD_NM'].map(mapping_dict)

# 매핑 안된 값는 원래 이름 유지
gdf['EMD_NM_정제'] = gdf['EMD_NM_정제'].fillna(gdf['EMD_NM'])

gdf['EMD_NM_정제'] = gdf['EMD_NM'].map(mapping_dict)

# 매핑 안된 값는 원래 이름 유지
gdf['EMD_NM_정제'] = gdf['EMD_NM_정제'].fillna(gdf['EMD_NM'])

gdf['정제읍면동'] = gdf['EMD_NM'].apply(clean_emd_nm)

emd_nm_list = gdf['EMD_NM'].unique().tolist()

# pop_df['읍면동명'] 리스트
eupmyeondong_list = pop_df['읍면동명'].unique().tolist()

# emd_nm에는 있는데 읍면동명에는 없는 값
only_in_emd_nm = list(set(emd_nm_list) - set(eupmyeondong_list))
print("emd_nm에는 있는데 읍면동명에는 없는 값:", only_in_emd_nm)

# 읍면동명에는 있는데 emd_nm에는 없는 값
only_in_eupmyeondong = list(set(eupmyeondong_list) - set(emd_nm_list))
print("읍면동명에는 있는데 emd_nm에는 없는 값:", only_in_eupmyeondong)