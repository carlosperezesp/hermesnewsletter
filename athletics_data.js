// Datos manuales — Diamond League 2026
window.ATHLETICS_DATA = {
  UPDATED: "2026-06-09",
  IMPORTANCE: 7,
  SEASON: 2026,
  NEXT_MEETING: {
    name: "Bislett Games",
    location: "Oslo, Noruega",
    date: "2026-06-11",
    state: "upcoming"
  },
  GROUPS: [
    {
      id: "velocidad",
      label: "Velocidad",
      sub: "100m · 200m · 400m",
      events: [
        {
          id: "100m_m", name: "100m — H", gender: "M",
          wr: { mark: "9.58", athlete: "Usain Bolt", country: "JAM", year: 2009 },
          athletes: [
            { id: "kishane_thompson", name: "Kishane Thompson", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 100, sb: "9.74", pb: "9.74", prevRank: null },
            { id: "noah_lyles", name: "Noah Lyles", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 93, sb: "9.81", pb: "9.77", prevRank: null },
            { id: "oblique_seville", name: "Oblique Seville", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 86, sb: "9.85", pb: "9.85", prevRank: null },
          ]
        },
        {
          id: "100m_w", name: "100m — M", gender: "W",
          wr: { mark: "10.49", athlete: "Florence Griffith-Joyner", country: "USA", year: 1988 },
          athletes: [
            { id: "shacari_richardson", name: "Sha'Carri Richardson", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "10.65", pb: "10.65", prevRank: null },
            { id: "julien_alfred", name: "Julien Alfred", country: "LCA", teamCode: "LCA",
              primary: "#65CFFF", secondary: "#000000", colors: { primary: "#65CFFF", secondary: "#000000" },
              logo: "https://flagcdn.com/24x18/lc.png", activeScore: 93, sb: "10.72", pb: "10.72", prevRank: null },
            { id: "shericka_jackson", name: "Shericka Jackson", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 87, sb: "10.75", pb: "10.65", prevRank: null },
          ]
        },
        {
          id: "200m_m", name: "200m — H", gender: "M",
          wr: { mark: "19.19", athlete: "Usain Bolt", country: "JAM", year: 2009 },
          athletes: [
            { id: "letsile_tebogo", name: "Letsile Tebogo", country: "BOT", teamCode: "BOT",
              primary: "#75AADB", secondary: "#000000", colors: { primary: "#75AADB", secondary: "#000000" },
              logo: "https://flagcdn.com/24x18/bw.png", activeScore: 100, sb: "19.46", pb: "19.46", prevRank: null },
            { id: "erriyon_knighton", name: "Erriyon Knighton", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 93, sb: "19.53", pb: "19.49", prevRank: null },
            { id: "jereem_richards", name: "Jereem Richards", country: "TTO", teamCode: "TTO",
              primary: "#CE1126", secondary: "#000000", colors: { primary: "#CE1126", secondary: "#000000" },
              logo: "https://flagcdn.com/24x18/tt.png", activeScore: 85, sb: "19.68", pb: "19.58", prevRank: null },
          ]
        },
        {
          id: "200m_w", name: "200m — M", gender: "W",
          wr: { mark: "21.34", athlete: "Florence Griffith-Joyner", country: "USA", year: 1988 },
          athletes: [
            { id: "gabby_thomas", name: "Gabby Thomas", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "21.81", pb: "21.60", prevRank: null },
            { id: "shericka_jackson_200", name: "Shericka Jackson", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 94, sb: "21.92", pb: "21.41", prevRank: null },
            { id: "brittany_brown", name: "Brittany Brown", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 86, sb: "22.10", pb: "21.96", prevRank: null },
          ]
        },
        {
          id: "400m_m", name: "400m — H", gender: "M",
          wr: { mark: "43.03", athlete: "Wayde van Niekerk", country: "RSA", year: 2016 },
          athletes: [
            { id: "quincy_hall", name: "Quincy Hall", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "43.40", pb: "43.40", prevRank: null },
            { id: "matthew_hudson_smith", name: "Matthew Hudson-Smith", country: "GBR", teamCode: "GBR",
              primary: "#012169", secondary: "#FFFFFF", colors: { primary: "#012169", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/gb.png", activeScore: 93, sb: "43.73", pb: "43.73", prevRank: null },
            { id: "steven_gardiner", name: "Steven Gardiner", country: "BAH", teamCode: "BAH",
              primary: "#00778B", secondary: "#FFC72C", colors: { primary: "#00778B", secondary: "#FFC72C" },
              logo: "https://flagcdn.com/24x18/bs.png", activeScore: 86, sb: "43.85", pb: "43.85", prevRank: null },
          ]
        },
        {
          id: "400m_w", name: "400m — M", gender: "W",
          wr: { mark: "47.60", athlete: "Marita Koch", country: "GDR", year: 1985 },
          athletes: [
            { id: "marileidy_paulino", name: "Marileidy Paulino", country: "DOM", teamCode: "DOM",
              primary: "#002D62", secondary: "#CE1126", colors: { primary: "#002D62", secondary: "#CE1126" },
              logo: "https://flagcdn.com/24x18/do.png", activeScore: 100, sb: "48.17", pb: "48.17", prevRank: null },
            { id: "femke_bol", name: "Femke Bol", country: "NED", teamCode: "NED",
              primary: "#AE1C28", secondary: "#21468B", colors: { primary: "#AE1C28", secondary: "#21468B" },
              logo: "https://flagcdn.com/24x18/nl.png", activeScore: 94, sb: "48.36", pb: "48.36", prevRank: null },
            { id: "salwa_naser", name: "Salwa Eid Naser", country: "BRN", teamCode: "BRN",
              primary: "#CE1126", secondary: "#FFFFFF", colors: { primary: "#CE1126", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/bh.png", activeScore: 87, sb: "48.60", pb: "48.14", prevRank: null },
          ]
        },
      ]
    },
    {
      id: "vallas",
      label: "Vallas",
      sub: "110mV (H) · 100mV (M) · 400mV",
      events: [
        {
          id: "110mh_m", name: "110m vallas — H", gender: "M",
          wr: { mark: "12.80", athlete: "Aries Merritt", country: "USA", year: 2012 },
          athletes: [
            { id: "grant_holloway", name: "Grant Holloway", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "12.97", pb: "12.81", prevRank: null },
            { id: "rasheed_broadbell", name: "Rasheed Broadbell", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 92, sb: "13.08", pb: "13.01", prevRank: null },
            { id: "daniel_roberts", name: "Daniel Roberts", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 85, sb: "13.12", pb: "13.08", prevRank: null },
          ]
        },
        {
          id: "100mh_w", name: "100m vallas — M", gender: "W",
          wr: { mark: "12.12", athlete: "Tobi Amusan", country: "NGR", year: 2022 },
          athletes: [
            { id: "masai_russell", name: "Masai Russell", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "12.34", pb: "12.34", prevRank: null },
            { id: "cyrena_samba", name: "Cyrena Samba-Mayela", country: "FRA", teamCode: "FRA",
              primary: "#002395", secondary: "#ED2939", colors: { primary: "#002395", secondary: "#ED2939" },
              logo: "https://flagcdn.com/24x18/fr.png", activeScore: 93, sb: "12.38", pb: "12.38", prevRank: null },
            { id: "jasmine_camacho", name: "Jasmine Camacho-Quinn", country: "PUR", teamCode: "PUR",
              primary: "#EF3340", secondary: "#FFFFFF", colors: { primary: "#EF3340", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/pr.png", activeScore: 87, sb: "12.41", pb: "12.26", prevRank: null },
          ]
        },
        {
          id: "400mh_m", name: "400m vallas — H", gender: "M",
          wr: { mark: "45.94", athlete: "Karsten Warholm", country: "NOR", year: 2021 },
          athletes: [
            { id: "rai_benjamin", name: "Rai Benjamin", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "46.17", pb: "46.17", prevRank: null },
            { id: "karsten_warholm", name: "Karsten Warholm", country: "NOR", teamCode: "NOR",
              primary: "#EF2B2D", secondary: "#FFFFFF", colors: { primary: "#EF2B2D", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/no.png", activeScore: 95, sb: "46.52", pb: "45.94", prevRank: null },
            { id: "alison_dos_santos", name: "Alison dos Santos", country: "BRA", teamCode: "BRA",
              primary: "#009C3B", secondary: "#FFDF00", colors: { primary: "#009C3B", secondary: "#FFDF00" },
              logo: "https://flagcdn.com/24x18/br.png", activeScore: 87, sb: "46.72", pb: "46.72", prevRank: null },
          ]
        },
        {
          id: "400mh_w", name: "400m vallas — M", gender: "W",
          wr: { mark: "50.37", athlete: "Sydney McLaughlin-Levrone", country: "USA", year: 2024 },
          athletes: [
            { id: "sydney_mclaughlin", name: "Sydney McLaughlin-Levrone", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "50.43", pb: "50.37", prevRank: null },
            { id: "femke_bol_400mh", name: "Femke Bol", country: "NED", teamCode: "NED",
              primary: "#AE1C28", secondary: "#21468B", colors: { primary: "#AE1C28", secondary: "#21468B" },
              logo: "https://flagcdn.com/24x18/nl.png", activeScore: 90, sb: "51.45", pb: "51.45", prevRank: null },
            { id: "anna_cockrell", name: "Anna Cockrell", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 82, sb: "52.20", pb: "52.20", prevRank: null },
          ]
        },
      ]
    },
    {
      id: "fondo",
      label: "Medio Fondo · Fondo · Obstáculos",
      sub: "800m · 1500m · 5000m · 3000mO",
      events: [
        {
          id: "800m_m", name: "800m — H", gender: "M",
          wr: { mark: "1:40.91", athlete: "David Rudisha", country: "KEN", year: 2012 },
          athletes: [
            { id: "emmanuel_wanyonyi", name: "Emmanuel Wanyonyi", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 100, sb: "1:41.96", pb: "1:41.96", prevRank: null },
            { id: "marco_arop", name: "Marco Arop", country: "CAN", teamCode: "CAN",
              primary: "#FF0000", secondary: "#FFFFFF", colors: { primary: "#FF0000", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/ca.png", activeScore: 92, sb: "1:43.29", pb: "1:43.29", prevRank: null },
            { id: "djamel_sedjati", name: "Djamel Sedjati", country: "ALG", teamCode: "ALG",
              primary: "#006233", secondary: "#FFFFFF", colors: { primary: "#006233", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/dz.png", activeScore: 85, sb: "1:43.55", pb: "1:43.29", prevRank: null },
          ]
        },
        {
          id: "800m_w", name: "800m — M", gender: "W",
          wr: { mark: "1:53.28", athlete: "Jarmila Kratochvílová", country: "TCH", year: 1983 },
          athletes: [
            { id: "keely_hodgkinson", name: "Keely Hodgkinson", country: "GBR", teamCode: "GBR",
              primary: "#012169", secondary: "#FFFFFF", colors: { primary: "#012169", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/gb.png", activeScore: 100, sb: "1:55.04", pb: "1:55.04", prevRank: null },
            { id: "mary_moraa", name: "Mary Moraa", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 93, sb: "1:55.31", pb: "1:55.31", prevRank: null },
            { id: "athing_mu", name: "Athing Mu", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 86, sb: "1:55.99", pb: "1:55.04", prevRank: null },
          ]
        },
        {
          id: "1500m_m", name: "1500m — H", gender: "M",
          wr: { mark: "3:26.00", athlete: "Hicham El Guerrouj", country: "MAR", year: 1998 },
          athletes: [
            { id: "cole_hocker", name: "Cole Hocker", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "3:27.65", pb: "3:27.65", prevRank: null },
            { id: "jakob_ingebrigtsen", name: "Jakob Ingebrigtsen", country: "NOR", teamCode: "NOR",
              primary: "#EF2B2D", secondary: "#FFFFFF", colors: { primary: "#EF2B2D", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/no.png", activeScore: 96, sb: "3:27.95", pb: "3:26.73", prevRank: null },
            { id: "josh_kerr", name: "Josh Kerr", country: "GBR", teamCode: "GBR",
              primary: "#012169", secondary: "#FFFFFF", colors: { primary: "#012169", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/gb.png", activeScore: 91, sb: "3:28.10", pb: "3:27.79", prevRank: null },
          ]
        },
        {
          id: "1500m_w", name: "1500m — M", gender: "W",
          wr: { mark: "3:49.11", athlete: "Faith Kipyegon", country: "KEN", year: 2023 },
          athletes: [
            { id: "faith_kipyegon_1500", name: "Faith Kipyegon", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 100, sb: "3:49.11", pb: "3:49.11", prevRank: null },
            { id: "jessica_hull", name: "Jessica Hull", country: "AUS", teamCode: "AUS",
              primary: "#00008B", secondary: "#FFDD00", colors: { primary: "#00008B", secondary: "#FFDD00" },
              logo: "https://flagcdn.com/24x18/au.png", activeScore: 87, sb: "3:53.89", pb: "3:53.89", prevRank: null },
            { id: "gudaf_tsegay", name: "Gudaf Tsegay", country: "ETH", teamCode: "ETH",
              primary: "#078930", secondary: "#FCDD09", colors: { primary: "#078930", secondary: "#FCDD09" },
              logo: "https://flagcdn.com/24x18/et.png", activeScore: 82, sb: "3:54.20", pb: "3:54.01", prevRank: null },
          ]
        },
        {
          id: "5000m_m", name: "5000m — H", gender: "M",
          wr: { mark: "12:35.36", athlete: "Joshua Cheptegei", country: "UGA", year: 2020 },
          athletes: [
            { id: "jakob_ingebrigtsen_5k", name: "Jakob Ingebrigtsen", country: "NOR", teamCode: "NOR",
              primary: "#EF2B2D", secondary: "#FFFFFF", colors: { primary: "#EF2B2D", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/no.png", activeScore: 100, sb: "12:44.09", pb: "12:44.09", prevRank: null },
            { id: "grant_fisher", name: "Grant Fisher", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 93, sb: "12:46.00", pb: "12:46.00", prevRank: null },
            { id: "nicholas_kimeli", name: "Nicholas Kimeli", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 87, sb: "12:46.79", pb: "12:46.79", prevRank: null },
          ]
        },
        {
          id: "5000m_w", name: "5000m — M", gender: "W",
          wr: { mark: "14:00.21", athlete: "Faith Kipyegon", country: "KEN", year: 2024 },
          athletes: [
            { id: "beatrice_chebet", name: "Beatrice Chebet", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 100, sb: "14:05.29", pb: "14:05.29", prevRank: null },
            { id: "faith_kipyegon_5k", name: "Faith Kipyegon", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 97, sb: "14:00.21", pb: "14:00.21", prevRank: null },
            { id: "nadia_battocletti", name: "Nadia Battocletti", country: "ITA", teamCode: "ITA",
              primary: "#009246", secondary: "#CE2B37", colors: { primary: "#009246", secondary: "#CE2B37" },
              logo: "https://flagcdn.com/24x18/it.png", activeScore: 83, sb: "14:16.31", pb: "14:16.31", prevRank: null },
          ]
        },
        {
          id: "3000msc_m", name: "3000m obstáculos — H", gender: "M",
          wr: { mark: "7:52.11", athlete: "Lamecha Girma", country: "ETH", year: 2023 },
          athletes: [
            { id: "el_bakkali", name: "Soufiane El Bakkali", country: "MAR", teamCode: "MAR",
              primary: "#C1272D", secondary: "#006233", colors: { primary: "#C1272D", secondary: "#006233" },
              logo: "https://flagcdn.com/24x18/ma.png", activeScore: 100, sb: "8:06.03", pb: "8:06.03", prevRank: null },
            { id: "abraham_kibiwott", name: "Abraham Kibiwott", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 92, sb: "8:08.41", pb: "8:08.41", prevRank: null },
            { id: "lamecha_girma", name: "Lamecha Girma", country: "ETH", teamCode: "ETH",
              primary: "#078930", secondary: "#FCDD09", colors: { primary: "#078930", secondary: "#FCDD09" },
              logo: "https://flagcdn.com/24x18/et.png", activeScore: 88, sb: "8:09.15", pb: "7:52.11", prevRank: null },
          ]
        },
        {
          id: "3000msc_w", name: "3000m obstáculos — M", gender: "W",
          wr: { mark: "8:44.32", athlete: "Beatrice Chepkoech", country: "KEN", year: 2018 },
          athletes: [
            { id: "winfred_yavi", name: "Winfred Yavi", country: "BRN", teamCode: "BRN",
              primary: "#CE1126", secondary: "#FFFFFF", colors: { primary: "#CE1126", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/bh.png", activeScore: 100, sb: "8:54.29", pb: "8:54.29", prevRank: null },
            { id: "faith_cherotich", name: "Faith Cherotich", country: "KEN", teamCode: "KEN",
              primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
              logo: "https://flagcdn.com/24x18/ke.png", activeScore: 91, sb: "8:55.09", pb: "8:55.09", prevRank: null },
            { id: "peruth_chemutai", name: "Peruth Chemutai", country: "UGA", teamCode: "UGA",
              primary: "#000000", secondary: "#FCDC04", colors: { primary: "#000000", secondary: "#FCDC04" },
              logo: "https://flagcdn.com/24x18/ug.png", activeScore: 84, sb: "8:57.39", pb: "8:57.39", prevRank: null },
          ]
        },
      ]
    },
    {
      id: "saltos",
      label: "Saltos",
      sub: "Altura · Pértiga · Longitud · Triple",
      events: [
        {
          id: "hj_m", name: "Salto de altura — H", gender: "M",
          wr: { mark: "2.45m", athlete: "Javier Sotomayor", country: "CUB", year: 1993 },
          athletes: [
            { id: "hamish_kerr", name: "Hamish Kerr", country: "NZL", teamCode: "NZL",
              primary: "#00247D", secondary: "#CC0000", colors: { primary: "#00247D", secondary: "#CC0000" },
              logo: "https://flagcdn.com/24x18/nz.png", activeScore: 100, sb: "2.35m", pb: "2.36m", prevRank: null },
            { id: "barshim", name: "Mutaz Essa Barshim", country: "QAT", teamCode: "QAT",
              primary: "#8D1B3D", secondary: "#FFFFFF", colors: { primary: "#8D1B3D", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/qa.png", activeScore: 95, sb: "2.34m", pb: "2.43m", prevRank: null },
            { id: "shelby_mcewan", name: "Shelby McEwen", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 87, sb: "2.33m", pb: "2.33m", prevRank: null },
          ]
        },
        {
          id: "hj_w", name: "Salto de altura — M", gender: "W",
          wr: { mark: "2.10m", athlete: "Yaroslava Mahuchikh", country: "UKR", year: 2024 },
          athletes: [
            { id: "mahuchikh", name: "Yaroslava Mahuchikh", country: "UKR", teamCode: "UKR",
              primary: "#005BBB", secondary: "#FFD500", colors: { primary: "#005BBB", secondary: "#FFD500" },
              logo: "https://flagcdn.com/24x18/ua.png", activeScore: 100, sb: "2.05m", pb: "2.10m", prevRank: null },
            { id: "nicola_olyslagers", name: "Nicola Olyslagers", country: "AUS", teamCode: "AUS",
              primary: "#00008B", secondary: "#FFDD00", colors: { primary: "#00008B", secondary: "#FFDD00" },
              logo: "https://flagcdn.com/24x18/au.png", activeScore: 92, sb: "2.00m", pb: "2.00m", prevRank: null },
            { id: "eleanor_patterson", name: "Eleanor Patterson", country: "AUS", teamCode: "AUS",
              primary: "#00008B", secondary: "#FFDD00", colors: { primary: "#00008B", secondary: "#FFDD00" },
              logo: "https://flagcdn.com/24x18/au.png", activeScore: 84, sb: "1.97m", pb: "2.02m", prevRank: null },
          ]
        },
        {
          id: "pv_m", name: "Salto con pértiga — H", gender: "M",
          wr: { mark: "6.25m", athlete: "Armand Duplantis", country: "SWE", year: 2024 },
          athletes: [
            { id: "mondo_duplantis", name: "Armand Duplantis", country: "SWE", teamCode: "SWE",
              primary: "#006AA7", secondary: "#FECC02", colors: { primary: "#006AA7", secondary: "#FECC02" },
              logo: "https://flagcdn.com/24x18/se.png", activeScore: 100, sb: "6.21m", pb: "6.25m", prevRank: null },
            { id: "sam_kendricks", name: "Sam Kendricks", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 85, sb: "5.97m", pb: "6.00m", prevRank: null },
            { id: "obiena", name: "Ernest John Obiena", country: "PHI", teamCode: "PHI",
              primary: "#0038A8", secondary: "#CE1126", colors: { primary: "#0038A8", secondary: "#CE1126" },
              logo: "https://flagcdn.com/24x18/ph.png", activeScore: 78, sb: "5.92m", pb: "6.00m", prevRank: null },
          ]
        },
        {
          id: "pv_w", name: "Salto con pértiga — M", gender: "W",
          wr: { mark: "5.06m", athlete: "Yelena Isinbayeva", country: "RUS", year: 2009 },
          athletes: [
            { id: "nina_kennedy", name: "Nina Kennedy", country: "AUS", teamCode: "AUS",
              primary: "#00008B", secondary: "#FFDD00", colors: { primary: "#00008B", secondary: "#FFDD00" },
              logo: "https://flagcdn.com/24x18/au.png", activeScore: 100, sb: "4.93m", pb: "4.93m", prevRank: null },
            { id: "alysha_newman", name: "Alysha Newman", country: "CAN", teamCode: "CAN",
              primary: "#FF0000", secondary: "#FFFFFF", colors: { primary: "#FF0000", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/ca.png", activeScore: 93, sb: "4.90m", pb: "4.95m", prevRank: null },
            { id: "sandi_morris", name: "Sandi Morris", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 86, sb: "4.88m", pb: "5.00m", prevRank: null },
          ]
        },
        {
          id: "lj_m", name: "Salto de longitud — H", gender: "M",
          wr: { mark: "8.95m", athlete: "Mike Powell", country: "USA", year: 1991 },
          athletes: [
            { id: "tentoglou", name: "Miltiadis Tentoglou", country: "GRE", teamCode: "GRE",
              primary: "#0D5EAF", secondary: "#FFFFFF", colors: { primary: "#0D5EAF", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/gr.png", activeScore: 100, sb: "8.32m", pb: "8.60m", prevRank: null },
            { id: "wayne_pinnock", name: "Wayne Pinnock", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 91, sb: "8.22m", pb: "8.22m", prevRank: null },
            { id: "mattia_furlani", name: "Mattia Furlani", country: "ITA", teamCode: "ITA",
              primary: "#009246", secondary: "#CE2B37", colors: { primary: "#009246", secondary: "#CE2B37" },
              logo: "https://flagcdn.com/24x18/it.png", activeScore: 85, sb: "8.19m", pb: "8.26m", prevRank: null },
          ]
        },
        {
          id: "lj_w", name: "Salto de longitud — M", gender: "W",
          wr: { mark: "7.52m", athlete: "Galina Chistyakova", country: "URS", year: 1988 },
          athletes: [
            { id: "tara_davis", name: "Tara Davis-Woodhall", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "7.05m", pb: "7.10m", prevRank: null },
            { id: "ese_brume", name: "Ese Brume", country: "NGR", teamCode: "NGR",
              primary: "#008751", secondary: "#FFFFFF", colors: { primary: "#008751", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/ng.png", activeScore: 91, sb: "6.98m", pb: "7.02m", prevRank: null },
            { id: "malaika_mihambo", name: "Malaika Mihambo", country: "GER", teamCode: "GER",
              primary: "#000000", secondary: "#DD0000", colors: { primary: "#000000", secondary: "#DD0000" },
              logo: "https://flagcdn.com/24x18/de.png", activeScore: 84, sb: "6.95m", pb: "7.30m", prevRank: null },
          ]
        },
        {
          id: "tj_m", name: "Triple salto — H", gender: "M",
          wr: { mark: "18.29m", athlete: "Jonathan Edwards", country: "GBR", year: 1995 },
          athletes: [
            { id: "jordan_diaz", name: "Jordan Diaz", country: "ESP", teamCode: "ESP",
              primary: "#AA151B", secondary: "#F1BF00", colors: { primary: "#AA151B", secondary: "#F1BF00" },
              logo: "https://flagcdn.com/24x18/es.png", activeScore: 100, sb: "17.78m", pb: "17.86m", prevRank: null },
            { id: "andy_diaz", name: "Andy Díaz Hernández", country: "ITA", teamCode: "ITA",
              primary: "#009246", secondary: "#CE2B37", colors: { primary: "#009246", secondary: "#CE2B37" },
              logo: "https://flagcdn.com/24x18/it.png", activeScore: 96, sb: "17.72m", pb: "17.84m", prevRank: null },
            { id: "pedro_pichardo", name: "Pedro Pichardo", country: "POR", teamCode: "POR",
              primary: "#006600", secondary: "#FF0000", colors: { primary: "#006600", secondary: "#FF0000" },
              logo: "https://flagcdn.com/24x18/pt.png", activeScore: 89, sb: "17.61m", pb: "17.98m", prevRank: null },
          ]
        },
        {
          id: "tj_w", name: "Triple salto — M", gender: "W",
          wr: { mark: "15.67m", athlete: "Yulimar Rojas", country: "VEN", year: 2021 },
          athletes: [
            { id: "yulimar_rojas", name: "Yulimar Rojas", country: "VEN", teamCode: "VEN",
              primary: "#CF142B", secondary: "#002868", colors: { primary: "#CF142B", secondary: "#002868" },
              logo: "https://flagcdn.com/24x18/ve.png", activeScore: 100, sb: "15.42m", pb: "15.67m", prevRank: null },
            { id: "thea_lafond", name: "Thea LaFond", country: "DMA", teamCode: "DMA",
              primary: "#009E60", secondary: "#000000", colors: { primary: "#009E60", secondary: "#000000" },
              logo: "https://flagcdn.com/24x18/dm.png", activeScore: 90, sb: "15.02m", pb: "15.02m", prevRank: null },
            { id: "shanieka_ricketts", name: "Shanieka Ricketts", country: "JAM", teamCode: "JAM",
              primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
              logo: "https://flagcdn.com/24x18/jm.png", activeScore: 83, sb: "14.92m", pb: "14.96m", prevRank: null },
          ]
        },
      ]
    },
    {
      id: "lanzamientos",
      label: "Lanzamientos",
      sub: "Peso · Disco · Jabalina",
      events: [
        {
          id: "sp_m", name: "Lanzamiento de peso — H", gender: "M",
          wr: { mark: "23.37m", athlete: "Ryan Crouser", country: "USA", year: 2021 },
          athletes: [
            { id: "ryan_crouser", name: "Ryan Crouser", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "22.84m", pb: "23.37m", prevRank: null },
            { id: "joe_kovacs", name: "Joe Kovacs", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 91, sb: "22.67m", pb: "22.91m", prevRank: null },
            { id: "tom_walsh", name: "Tom Walsh", country: "NZL", teamCode: "NZL",
              primary: "#00247D", secondary: "#CC0000", colors: { primary: "#00247D", secondary: "#CC0000" },
              logo: "https://flagcdn.com/24x18/nz.png", activeScore: 83, sb: "22.26m", pb: "22.90m", prevRank: null },
          ]
        },
        {
          id: "sp_w", name: "Lanzamiento de peso — M", gender: "W",
          wr: { mark: "22.63m", athlete: "Natalya Lisovskaya", country: "URS", year: 1987 },
          athletes: [
            { id: "yemisi_ogunleye", name: "Yemisi Ogunleye", country: "GER", teamCode: "GER",
              primary: "#000000", secondary: "#DD0000", colors: { primary: "#000000", secondary: "#DD0000" },
              logo: "https://flagcdn.com/24x18/de.png", activeScore: 100, sb: "20.15m", pb: "20.15m", prevRank: null },
            { id: "chase_ealey", name: "Chase Ealey", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 93, sb: "19.95m", pb: "20.12m", prevRank: null },
            { id: "sarah_mitton", name: "Sarah Mitton", country: "CAN", teamCode: "CAN",
              primary: "#FF0000", secondary: "#FFFFFF", colors: { primary: "#FF0000", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/ca.png", activeScore: 85, sb: "19.80m", pb: "20.31m", prevRank: null },
          ]
        },
        {
          id: "dt_m", name: "Lanzamiento de disco — H", gender: "M",
          wr: { mark: "74.35m", athlete: "Mykolas Alekna", country: "LTU", year: 2024 },
          athletes: [
            { id: "mykolas_alekna", name: "Mykolas Alekna", country: "LTU", teamCode: "LTU",
              primary: "#FDB913", secondary: "#006A44", colors: { primary: "#FDB913", secondary: "#006A44" },
              logo: "https://flagcdn.com/24x18/lt.png", activeScore: 100, sb: "71.25m", pb: "74.35m", prevRank: null },
            { id: "kristjan_ceh", name: "Kristjan Čeh", country: "SLO", teamCode: "SLO",
              primary: "#003DA5", secondary: "#FFFFFF", colors: { primary: "#003DA5", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/si.png", activeScore: 89, sb: "69.45m", pb: "71.86m", prevRank: null },
            { id: "andrius_gudzius", name: "Andrius Gudžius", country: "LTU", teamCode: "LTU",
              primary: "#FDB913", secondary: "#006A44", colors: { primary: "#FDB913", secondary: "#006A44" },
              logo: "https://flagcdn.com/24x18/lt.png", activeScore: 82, sb: "68.90m", pb: "69.59m", prevRank: null },
          ]
        },
        {
          id: "dt_w", name: "Lanzamiento de disco — M", gender: "W",
          wr: { mark: "76.80m", athlete: "Gabriele Reinsch", country: "GDR", year: 1988 },
          athletes: [
            { id: "valarie_allman", name: "Valarie Allman", country: "USA", teamCode: "USA",
              primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/us.png", activeScore: 100, sb: "69.50m", pb: "71.46m", prevRank: null },
            { id: "kristin_pudenz", name: "Kristin Pudenz", country: "GER", teamCode: "GER",
              primary: "#000000", secondary: "#DD0000", colors: { primary: "#000000", secondary: "#DD0000" },
              logo: "https://flagcdn.com/24x18/de.png", activeScore: 90, sb: "67.17m", pb: "67.87m", prevRank: null },
            { id: "bin_feng", name: "Bin Feng", country: "CHN", teamCode: "CHN",
              primary: "#DE2910", secondary: "#FFDE00", colors: { primary: "#DE2910", secondary: "#FFDE00" },
              logo: "https://flagcdn.com/24x18/cn.png", activeScore: 82, sb: "65.56m", pb: "66.37m", prevRank: null },
          ]
        },
        {
          id: "jt_m", name: "Lanzamiento de jabalina — H", gender: "M",
          wr: { mark: "98.48m", athlete: "Jan Železný", country: "CZE", year: 1996 },
          athletes: [
            { id: "arshad_nadeem", name: "Arshad Nadeem", country: "PAK", teamCode: "PAK",
              primary: "#01411C", secondary: "#FFFFFF", colors: { primary: "#01411C", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/pk.png", activeScore: 100, sb: "92.45m", pb: "92.97m", prevRank: null },
            { id: "neeraj_chopra", name: "Neeraj Chopra", country: "IND", teamCode: "IND",
              primary: "#FF9933", secondary: "#FFFFFF", colors: { primary: "#FF9933", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/in.png", activeScore: 93, sb: "89.45m", pb: "89.94m", prevRank: null },
            { id: "jakub_vadlejch", name: "Jakub Vadlejch", country: "CZE", teamCode: "CZE",
              primary: "#D7141A", secondary: "#11457E", colors: { primary: "#D7141A", secondary: "#11457E" },
              logo: "https://flagcdn.com/24x18/cz.png", activeScore: 85, sb: "88.50m", pb: "90.88m", prevRank: null },
          ]
        },
        {
          id: "jt_w", name: "Lanzamiento de jabalina — M", gender: "W",
          wr: { mark: "72.28m", athlete: "Barbora Špotáková", country: "CZE", year: 2008 },
          athletes: [
            { id: "haruka_kitaguchi", name: "Haruka Kitaguchi", country: "JPN", teamCode: "JPN",
              primary: "#BC002D", secondary: "#FFFFFF", colors: { primary: "#BC002D", secondary: "#FFFFFF" },
              logo: "https://flagcdn.com/24x18/jp.png", activeScore: 100, sb: "65.80m", pb: "66.00m", prevRank: null },
            { id: "adriana_vilagos", name: "Adriana Vílagos", country: "SRB", teamCode: "SRB",
              primary: "#C6363C", secondary: "#0C4076", colors: { primary: "#C6363C", secondary: "#0C4076" },
              logo: "https://flagcdn.com/24x18/rs.png", activeScore: 91, sb: "64.52m", pb: "64.52m", prevRank: null },
            { id: "kelsey_lee_barber", name: "Kelsey-Lee Barber", country: "AUS", teamCode: "AUS",
              primary: "#00008B", secondary: "#FFDD00", colors: { primary: "#00008B", secondary: "#FFDD00" },
              logo: "https://flagcdn.com/24x18/au.png", activeScore: 83, sb: "63.90m", pb: "66.91m", prevRank: null },
          ]
        },
      ]
    },
  ],
  LEGENDS: [
    { id: "bolt", name: "Usain Bolt", country: "JAM", teamCode: "JAM",
      primary: "#000000", secondary: "#FFCC00", colors: { primary: "#000000", secondary: "#FFCC00" },
      logo: "https://flagcdn.com/24x18/jm.png", legendScore: 100, active: false,
      events: "100m · 200m", note: "8 oros olímpicos · 11 títulos mundiales · WR 9.58 y 19.19" },
    { id: "carl_lewis", name: "Carl Lewis", country: "USA", teamCode: "USA",
      primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
      logo: "https://flagcdn.com/24x18/us.png", legendScore: 92, active: false,
      events: "100m · LJ", note: "9 oros olímpicos · 10 títulos mundiales · dominó dos décadas" },
    { id: "flo_jo", name: "Florence Griffith-Joyner", country: "USA", teamCode: "USA",
      primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
      logo: "https://flagcdn.com/24x18/us.png", legendScore: 88, active: false,
      events: "100m · 200m", note: "WR 10.49 y 21.34 (1988, vigentes) · 3 oros en Seúl 88" },
    { id: "michael_johnson", name: "Michael Johnson", country: "USA", teamCode: "USA",
      primary: "#B22234", secondary: "#FFFFFF", colors: { primary: "#B22234", secondary: "#FFFFFF" },
      logo: "https://flagcdn.com/24x18/us.png", legendScore: 85, active: false,
      events: "200m · 400m", note: "WR 200m + 400m · 4 oros olímpicos · rey del sprint largo" },
    { id: "kipchoge", name: "Eliud Kipchoge", country: "KEN", teamCode: "KEN",
      primary: "#006600", secondary: "#CC0001", colors: { primary: "#006600", secondary: "#CC0001" },
      logo: "https://flagcdn.com/24x18/ke.png", legendScore: 83, active: true,
      events: "5000m · Maratón", note: "2 oros olímpicos · sub-2h (no oficial) · el maratoniano más grande" },
    { id: "bubka", name: "Sergey Bubka", country: "UKR", teamCode: "UKR",
      primary: "#005BBB", secondary: "#FFD500", colors: { primary: "#005BBB", secondary: "#FFD500" },
      logo: "https://flagcdn.com/24x18/ua.png", legendScore: 80, active: false,
      events: "Pértiga", note: "6 títulos mundiales consecutivos · 35 records del mundo · 6.14m" },
    { id: "el_guerrouj", name: "Hicham El Guerrouj", country: "MAR", teamCode: "MAR",
      primary: "#C1272D", secondary: "#006233", colors: { primary: "#C1272D", secondary: "#006233" },
      logo: "https://flagcdn.com/24x18/ma.png", legendScore: 77, active: false,
      events: "1500m · Milla", note: "WR 1500m (3:26.00, 1998, vigente) · doble oro en Atenas 2004" },
    { id: "zelezny", name: "Jan Železný", country: "CZE", teamCode: "CZE",
      primary: "#D7141A", secondary: "#11457E", colors: { primary: "#D7141A", secondary: "#11457E" },
      logo: "https://flagcdn.com/24x18/cz.png", legendScore: 74, active: false,
      events: "Jabalina", note: "WR 98.48m (1996, vigente) · 3 oros olímpicos · el lanzador más técnico" },
    { id: "marita_koch", name: "Marita Koch", country: "GER", teamCode: "GER",
      primary: "#000000", secondary: "#DD0000", colors: { primary: "#000000", secondary: "#DD0000" },
      logo: "https://flagcdn.com/24x18/de.png", legendScore: 71, active: false,
      events: "400m", note: "WR 47.60 (1985, 40+ años vigente) · reina absoluta del 400m en los 80" },
    { id: "gebrselassie", name: "Haile Gebrselassie", country: "ETH", teamCode: "ETH",
      primary: "#078930", secondary: "#FCDD09", colors: { primary: "#078930", secondary: "#FCDD09" },
      logo: "https://flagcdn.com/24x18/et.png", legendScore: 68, active: false,
      events: "5000m · 10000m", note: "27 records del mundo · 2 oros olímpicos · el maestro del fondo" },
  ]
};
