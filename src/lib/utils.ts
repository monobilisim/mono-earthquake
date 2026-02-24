import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChild<T> = T extends { child?: any } ? Omit<T, 'child'> : T;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChildren<T> = T extends { children?: any } ? Omit<T, 'children'> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };

export function generateRandomToken(length: number, alphabet: boolean = false) {
  let ALPHABET = '0123456789';
  if (alphabet) {
    ALPHABET += 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
  }
  const bytes = new Uint8Array(length);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => ALPHABET[b % ALPHABET.length]).join('');
}

export function stripNonAlnumAscii(s: string): string {
  return s.replace(/[^A-Za-z0-9]/g, '');
}

export function isPortrait(window: Window) {
  return window.innerHeight > window.innerWidth;
}

const Provinces = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"].toSorted();

const MapTurkeyJsonProvinces = {
  "Adana": "Adana",
  "Adiyaman": "Adıyaman",
  "Afyon": "Afyonkarahisar",
  "Agri": "Ağrı",
  "Aksaray": "Aksaray",
  "Amasya": "Amasya",
  "Ankara": "Ankara",
  "Antalya": "Antalya",
  "Ardahan": "Ardahan",
  "Artvin": "Artvin",
  "Aydin": "Aydın",
  "Balikesir": "Balıkesir",
  "Bartın": "Bartın",
  "Batman": "Batman",
  "Bayburt": "Bayburt",
  "Bilecik": "Bilecik",
  "Bingöl": "Bingöl",
  "Bitlis": "Bitlis",
  "Bolu": "Bolu",
  "Burdur": "Burdur",
  "Bursa": "Bursa",
  "Denizli": "Denizli",
  "Diyarbakir": "Diyarbakır",
  "Düzce": "Düzce",
  "Edirne": "Edirne",
  "Elazığ": "Elazığ",
  "Erzincan": "Erzincan",
  "Erzurum": "Erzurum",
  "Eskisehir": "Eskişehir",
  "Gaziantep": "Gaziantep",
  "Giresun": "Giresun",
  "Gümüshane": "Gümüşhane",
  "Hakkari": "Hakkari",
  "Hatay": "Hatay",
  "Isparta": "Isparta",
  "Istanbul": "İstanbul",
  "Izmir": "İzmir",
  "Iğdır": "Iğdır",
  "K.Maras": "Kahramanmaraş",
  "Karabük": "Karabük",
  "Karaman": "Karaman",
  "Kars": "Kars",
  "Kastamonu": "Kastamonu",
  "Kayseri": "Kayseri",
  "Kilis": "Kilis",
  "Kinkkale": "Kırıkkale",
  "Kirklareli": "Kırklareli",
  "Kirsehir": "Kırşehir",
  "Kocaeli": "Kocaeli",
  "Konya": "Konya",
  "Kütahya": "Kütahya",
  "Malatya": "Malatya",
  "Manisa": "Manisa",
  "Mardin": "Mardin",
  "Mersin": "Mersin",
  "Mugla": "Muğla",
  "Mus": "Muş",
  "Nevsehir": "Nevşehir",
  "Nigde": "Niğde",
  "Ordu": "Ordu",
  "Osmaniye": "Osmaniye",
  "Rize": "Rize",
  "Sakarya": "Sakarya",
  "Samsun": "Samsun",
  "Sanliurfa": "Şanlıurfa",
  "Siirt": "Siirt",
  "Sinop": "Sinop",
  "Sirnak": "Şırnak",
  "Sivas": "Sivas",
  "Tekirdag": "Tekirdağ",
  "Tokat": "Tokat",
  "Trabzon": "Trabzon",
  "Tunceli": "Tunceli",
  "Usak": "Uşak",
  "Van": "Van",
  "Yalova": "Yalova",
  "Yozgat": "Yozgat",
  "Zinguldak": "Zonguldak",
  "Çanakkale": "Çanakkale",
  "Çankiri": "Çankırı",
  "Çorum": "Çorum"
};

export { Provinces, MapTurkeyJsonProvinces };
