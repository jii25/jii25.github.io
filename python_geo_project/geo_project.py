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
df = pd.read_csv("market.csv", encoding='cp949')  # 파일명에 맞게 조정

jeju_markets = df[df['시도'] == '제주특별자치도'].copy()
jeju_markets = jeju_markets[['시장명', '도로명주소']].dropna()

# 온누리 상품권 가맹점 데이터 불러오기
onuri_df = pd.read_csv("onuri.csv", encoding='cp949')  # onuri 파일
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

# GeoJSON 파일 경로 (제주 읍면동 경계 파일 준비 필요)
geo_df = "jeju_eupmyeondong.shp"
gdf = gpd.read_file(geo_df, encoding='cp949')

# 읍면동명 정제 함수
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
gdf['정제읍면동'] = gdf['EMD_NM'].map(mapping_dict)
gdf['정제읍면동'] = gdf['정제읍면동'].fillna(gdf['EMD_NM'])

# 남녀 업종별 이용금액 top3 추출
grouped = pop_df.groupby(['읍면동명', '성별', '업종명'])['이용금액'].sum().reset_index()
grouped['순위'] = grouped.groupby(['읍면동명', '성별'])['이용금액'].rank(ascending=False, method='first')
top3 = grouped[grouped['순위'] <= 3]

# 읍면동별 팝업 html 생성 함수 (남성+여성)
def make_gender_top3_text(df, dong_name):
    sub = df[df['읍면동명'] == dong_name]
    if sub.empty:
        return "데이터 없음"
    
    males = sub[sub['성별'] == '남성'].sort_values('순위')
    females = sub[sub['성별'] == '여성'].sort_values('순위')

    html = "<b>업종별 카드 이용금액 Top3</b><br><br>"
    html += "<b>남성</b><br>"
    for i, row in enumerate(males.itertuples(), 1):
        html += f"{i}. {row.업종명} - {int(row.이용금액):,}원<br>"
    if males.empty:
        html += "데이터 없음<br>"
    
    html += "<br><b>여성</b><br>"
    for i, row in enumerate(females.itertuples(), 1):
        html += f"{i}. {row.업종명} - {int(row.이용금액):,}원<br>"
    if females.empty:
        html += "데이터 없음<br>"
    return html

# 팝업 html 컬럼 추가
popup_htmls = []
for idx, row in gdf.iterrows():
    dong = row['정제읍면동']
    popup_htmls.append(make_gender_top3_text(top3, dong))
gdf['popup_html'] = popup_htmls

# 스타일 함수 (데이터 있으면 파란색, 없으면 회색)
def style_function(feature):
    dong = feature['properties']['정제읍면동']
    if dong in top3['읍면동명'].values:
        return {'fillColor': 'white', 'color': 'gray', 'weight': 0.5, 'fillOpacity': 0}
    else:
        return {'fillColor': 'white', 'color': 'gray', 'weight': 0.5, 'fillOpacity': 0}

folium.GeoJson(
    gdf,
    name='읍면동 경계',
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(fields=['EMD_NM'], aliases=['읍면동']),
    popup=folium.GeoJsonPopup(fields=['popup_html'], labels=False, localize=True)
).add_to(m)

for _, row in jeju_markets.iterrows():
    if pd.notnull(row['위도']) and pd.notnull(row['경도']):
        matched_onuri = onuri_df[onuri_df['소재지'].str.contains(row['도로명주소'], na=False)].copy()
        
        # 취급품목 기준 오름차순 정렬
        matched_onuri.sort_values('취급품목', inplace=True)
        
        popup_html = f"<b>{row['시장명']}</b><br>{row['도로명주소']}<br><br>"

        if not matched_onuri.empty:
            popup_html += "<b>온누리 상품권 가능 매장</b><br>"
            
            # '노점'인 점포명 중복 시 번호 붙이기 위한 카운터 초기화
            nojeom_counter = 1
            
            for _, o_row in matched_onuri.iterrows():
                store_name = o_row['가맹점명']
                # '노점'일 때만 번호 붙임
                if store_name == '노점':
                    store_name = f"노점 #{nojeom_counter}"
                    nojeom_counter += 1
                
                popup_html += f"• {store_name} — {o_row['취급품목']}<br>"
        else:
            popup_html += "온누리 상품권 가능 매장 정보 없음<br>"
        
        iframe = folium.IFrame(html=popup_html, width=350, height=200)
        popup = folium.Popup(iframe, max_width=350)

        folium.Marker(
            location=[row['위도'], row['경도']],
            popup=popup,
            icon=folium.Icon(color="blue", icon="shopping-cart", prefix="fa")
        ).add_to(m)

# 결과 저장
m.save("jeju_markets_kakao_map.html")
print("지도가 생성되었습니다: jeju_markets_kakao_map.html")
