from fake_useragent import UserAgent
from urlextract import URLExtract
from bs4 import BeautifulSoup
from pathlib import Path
import pandas as pd
import requests
import time
import os
from pprint import pprint

extractor = URLExtract()
ua = UserAgent()
headers = {
    'Accept': '*/*',
    "User-Agent": ua.random
}


def get_preliminary_df():
    df_list = []
    for i in range(1, 23):
        try:
            url = f'https://www.zara.com/tr/tr/kadin-ayakkabilar-l1251.html?v1=2113973&page={i}'
            print(url)
            response = requests.get(url=url, headers=headers)
            soup = BeautifulSoup(response.content, 'lxml')
            product_grid = soup.find('section', class_='product-grid')
            lis = soup.find_all('li', class_='product-grid-block-dynamic__container')

            links = [li.a['href'] for li in lis]
            alts = [li.img['alt'] for li in lis]
            srcs = [li.img['src'] for li in lis]
            links_2 = [li.find('a', class_='product-link')['href']
                       if li.find('a', class_='product-link') is not None else 'no_price'
                       for li in lis]
            prices = [li.find('span', class_='money-amount__main').text
                      if li.find('span', class_='money-amount__main') is not None else 'no_price'
                      for li in lis]

            prod_dict = {
                'links': links,
                'alts': alts,
                'srcs': srcs,
                'links_2': links_2,
                'prices': prices,
            }
            df_list.append(pd.DataFrame(prod_dict))
            time.sleep(0.5)
        except Exception as e:
            print('Не удалось обработать страницу из-за ошибки:')
            print(e)

    df = pd.concat(df_list)

    return df


def get_complete_df(df):
    df_detailed_list = []

    links_todo = sorted(set(df.links))
    for idx, url in enumerate(links_todo):
        print(f'{idx + 1} из {len(links_todo)} -  {url}')
        try:
            response = requests.get(url=url, headers=headers)
            soup = BeautifulSoup(response.content, 'lxml')

            # Detail View (Photo links)
            try:
                dv = soup.find('div', class_='product-detail-view__main')
                lis = dv.find_all('li', class_='product-detail-images__image-wrapper')
                photo_links = [extractor.find_urls((li.picture.source['srcset'])) for li in lis]
            except:
                photo_links = '-----'
            try:
                secondary_products = soup.find_all('div', class_='product-detail-cross-selling__related-products')[-1]
                sp_links = [li.a['href'] for li in secondary_products]
            except:
                sp_links = ['-----']

            # Sidebar ()
            side_bar = soup.find('div', class_='product-detail-view__side-bar')
            try:
                title = side_bar.find('div', class_='product-detail-info__header').text
            except:
                title = '-----'
            try:
                description = side_bar.find('div', class_='expandable-text__inner-content').text
            except:
                description = '-----'
            try:
                color = side_bar.find('p', class_='product-detail-selected-color').text
            except:
                color = '-----'
            try:
                extra_info = side_bar.find('div', class_='product-detail-info__join-life-extra-info').text
            except:
                extra_info = '-----'
            try:
                price = side_bar.find('div', class_='money-amount price-formatted__price-amount').text
            except:
                price = '-----'
            try:
                lis = side_bar.find('div', class_='product-detail-size-selector__size-list-wrapper'). \
                    find_all('li', class_='product-detail-size-selector__size-list-item')
                sizes_dict = dict(zip([li.span.text for li in lis], [li['data-qa-action'] for li in lis]))
            except:
                sizes_dict = '-----'

            sku = url.split('.html').str[0].str.split('-').str[-1]

            print(len(sizes_dict))
            df_detailed_list.append(pd.DataFrame({
                'SKU': [sku],
                'title': [title],
                'description': [description],
                'color': [color],
                'extra_info': [extra_info],
                'price': [price],
                'sizes_dict': [sizes_dict],
                'url': [url],
                'photo_links': [photo_links],
                'sp_links': sp_links,
            }))
            time.sleep(0.5)
        except Exception as e:
            print(e)
            df_detailed_list.append(pd.DataFrame({
                'SKU': ['-----'],
                'title': ['-----'],
                'description': ['-----'],
                'color': ['-----'],
                'extra_info': ['-----'],
                'price': ['-----'],
                'sizes_dict': ['-----'],
                'url': [url],
                'photo_links': ['-----'],
                'sp_links': ['-----'],
            }))
    df_detailed = pd.concat(df_detailed_list)
    df_detailed['SKU'] = df_detailed.url.str.split('.html').str[0].str.split('-').str[-1]
    # df_detailed.to_excel('Zara_detailed.xlsx', index=False)

    return df_detailed


def save_photos(df_detailed):
    for idx, row in df_detailed[['photo_links', 'SKU']].sort_values(by='SKU').iterrows():
        if idx == 5:
            break
        for pictire_links in row.photo_links:
            for link in pictire_links:
                folder_name = './pics/' + row.SKU + '/' + link.split('/w/')[-1].split('/')[0]
                jpeg_name = link.split('.jpg')[0].split('/')[-1] + '.jpg'
                print(idx, len(df_detailed.index), row.SKU, link)
                if 'w/2048/' in link and 'http' in link and not os.path.exists(
                        folder_name + '/' + jpeg_name):  # Если файл еще не скачан
                    Path(folder_name).mkdir(parents=True, exist_ok=True)

                    response = requests.get(link, headers=headers)
                    if response.status_code:

                        fp = open(folder_name + '/' + jpeg_name, 'wb')
                        fp.write(response.content)
                        fp.close()
                    else:
                        print('не доступен', link)


def main():
    df = get_preliminary_df()
    df_detailed = get_complete_df(df)
    save_photos(df_detailed)


if __name__ == '__main__':
    main()
