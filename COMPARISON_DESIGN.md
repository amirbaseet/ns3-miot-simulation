# TASARIM DOKÜMANI: WSN vs MQTT-SN Adil Karşılaştırma
# =====================================================

## 1. GENEL PLAN

İki deney seti yapacağız:

### Deney Seti 1: Broker'sız (Sadece Uygulama Katmanı Karşılaştırması)

```
Scenario A (WSN):     Sensör --OnOff UDP--> CH (PacketSink)
Scenario B (MQTT-SN): Sensör --MQTT-SN---> CH (Gateway)
```

Amaç: "Aynı ağda, aynı topolojide, sadece uygulama katmanı değişince
       performans nasıl etkileniyor?"

### Deney Seti 2: Broker'lı (Tam Mimari Karşılaştırması)

```
Scenario A (WSN):     Sensör --UDP--> CH --UDP forward--> Sink
Scenario B (MQTT-SN): Sensör --MQTT-SN--> CH --MQTT-SN--> Broker
```

Amaç: "Gerçek hayat senaryosunda, veri merkeze kadar ulaşırken
       hangi mimari daha iyi performans gösteriyor?"


## 2. ORTAK PARAMETRELER (İki senaryoda da aynı)

```
Alan:           1000m x 1000m
WiFi:           802.11b Ad-Hoc, 20dBm
Routing:        AODV (HelloInterval=2s, RreqRetries=5, ActiveRouteTimeout=15s)
Simülasyon:     100 saniye
Node sayıları:  50, 100, 150, 200 sensör
CH oranı:       %10 (50→5CH, 100→10CH, 150→15CH, 200→20CH)
Seed:           42 (tekrarlanabilir sonuçlar)
```


## 3. FARKLILIKLAR

### Scenario A: WSN (Geleneksel)

```
Uygulama:    OnOffApplication
  - Tüm sensörler aynı hızda: 4 kbps
  - Paket boyutu: 512 byte
  - Sürekli gönderim (On=1s, Off=0s)
  
CH rolü:     PacketSink
  - Sadece paket alır ve sayar
  - Akıllı işlem yok

Broker'lı versiyonda CH ek olarak:
  - Aldığı her paketi UDP ile sink'e forward eder
  - Basit forwarding, priority yok
```

### Scenario B: MQTT-SN (IoT)

```
Uygulama:    MqttSnPublisher
  - 3 farklı sensör tipi:
    ECG:  250ms aralık, 128 byte, QoS=2 (HIGH)
    HR:   1s aralık, 64 byte, QoS=1 (MEDIUM)
    Temp: 5s aralık, 32 byte, QoS=0 (LOW)
  - Emergency detection (%0.5)
  
CH rolü:     MqttSnGateway
  - Header parse eder
  - Priority queue ile sıralar
  - QoS>0 için PUBACK gönderir
  - CONNACK gönderir

Broker'lı versiyonda CH ek olarak:
  - Priority sırasına göre broker'a forward eder
  - Broker istatistik tutar
```


## 4. DOSYA DEĞİŞİKLİKLERİ

### Değişiklik 1: MQTT-SN broker=false düzelt
Dosya: cluster-aodv-mqtt.cc

Problem: broker=false olduğunda sink node oluşturulmuyor ama
         PositionNodes() sink'e erişmeye çalışıyor → crash

Çözüm (pseudocode):
```
if broker == true:
    sink.Create(1)
    all.Add(sink)
    PositionNodes(sens, chs, sink, ...)    # sink var
else:
    # sink oluşturma
    PositionNodes(sens, chs, nCH, ...)     # sink parametresi yok
```

Aslında daha basit çözüm:
```
# Her zaman sink oluştur ama broker=false ise uygulama yükleme
sink.Create(1)
all.Add(sink)
PositionNodes(sens, chs, sink, ...)

if broker == true:
    Install broker app on sink
    Install forwarding on gateways
# else: sink var ama boş, sadece ağda duruyor (trafik üretmiyor)
```


### Değişiklik 2: WSN'e sink ekle
Dosya: cluster-aodv-nosink.cc

Yeni parametre: --useSink (true/false)

Pseudocode:
```
main():
    parse --useSink parameter (default: false)
    
    if useSink:
        create sensors + CHs + 1 sink
        position sink at center (500, 500)
    else:
        create sensors + CHs only
    
    // Trafik kurulumu
    for each sensor:
        install OnOff → nearest CH
    
    for each CH:
        install PacketSink (port 9)   # sensörlerden al
        
        if useSink:
            install OnOff → sink      # CH'den sink'e forward
            // CH hem alıcı hem gönderici olacak
    
    if useSink:
        install PacketSink on sink    # sink'te tüm verileri topla

    run simulation
    print results + sink statistics
```

CH'nin forwarding mantığı:
```
CH aynı anda iki iş yapıyor:
  1. Port 9'da dinle → sensörlerden gelen paketleri al
  2. Port 10'dan gönder → sink'e forward et (OnOff ile)

  Sensör --port 9--> [CH: PacketSink + OnOff forward] --port 10--> Sink
```


## 5. DENEY MATRİSİ

Toplam 16 simülasyon:

### Deney Seti 1: Broker'sız
```
| #  | Senaryo | Nodes | CH  | Broker | CSV dosya adı          |
|----|---------|-------|-----|--------|------------------------|
| 1  | WSN     | 50    | 5   | Yok    | exp1_wsn_50.csv        |
| 2  | WSN     | 100   | 10  | Yok    | exp1_wsn_100.csv       |
| 3  | WSN     | 150   | 15  | Yok    | exp1_wsn_150.csv       |
| 4  | WSN     | 200   | 20  | Yok    | exp1_wsn_200.csv       |
| 5  | MQTT-SN | 50    | 5   | Yok    | exp1_mqtt_50.csv       |
| 6  | MQTT-SN | 100   | 10  | Yok    | exp1_mqtt_100.csv      |
| 7  | MQTT-SN | 150   | 15  | Yok    | exp1_mqtt_150.csv      |
| 8  | MQTT-SN | 200   | 20  | Yok    | exp1_mqtt_200.csv      |
```

### Deney Seti 2: Broker'lı
```
| #  | Senaryo | Nodes | CH  | Broker | CSV dosya adı          |
|----|---------|-------|-----|--------|------------------------|
| 9  | WSN     | 50    | 5   | Var    | exp2_wsn_50.csv        |
| 10 | WSN     | 100   | 10  | Var    | exp2_wsn_100.csv       |
| 11 | WSN     | 150   | 15  | Var    | exp2_wsn_150.csv       |
| 12 | WSN     | 200   | 20  | Var    | exp2_wsn_200.csv       |
| 13 | MQTT-SN | 50    | 5   | Var    | exp2_mqtt_50.csv       |
| 14 | MQTT-SN | 100   | 10  | Var    | exp2_mqtt_100.csv      |
| 15 | MQTT-SN | 150   | 15  | Var    | exp2_mqtt_150.csv      |
| 16 | MQTT-SN | 200   | 20  | Var    | exp2_mqtt_200.csv      |
```

Not: Deney Seti 2'nin MQTT-SN kısmı zaten mevcut (mqtt_50...200).
     WSN broker'lı ve MQTT-SN broker'sız deneyler eksik.


## 6. KARŞILAŞTIRMA METRİKLERİ

Her deney için ölçülecek:
```
1. PDR (Packet Delivery Ratio) - %
2. End-to-End Delay - ms
3. Throughput - kbps
4. Dead Flows - adet
5. Jitter - ms
```

Üretilecek grafikler:
```
Deney Seti 1 (Broker'sız):
  - WSN vs MQTT-SN PDR (bar chart, 4 node sayısı)
  - WSN vs MQTT-SN Delay (bar chart)
  - WSN vs MQTT-SN PDR trend (line chart, nodes arttıkça)
  - WSN vs MQTT-SN Delay trend (line chart)
  - Özet tablo

Deney Seti 2 (Broker'lı):
  - Aynı 5 grafik

Karşılaştırma:
  - Broker etkisi: Broker'sız vs Broker'lı (WSN)
  - Broker etkisi: Broker'sız vs Broker'lı (MQTT-SN)
  - Master dashboard: 4 senaryo tek grafikte
```


## 7. UYGULAMA SIRASI

```
Adım 1: cluster-aodv-mqtt.cc → broker=false düzelt
         Test: ./ns3 run "cluster-aodv-mqtt --nSensors=30 --nCH=3 --broker=false"
         Beklenen: Çalışır, sink yok ama crash yok

Adım 2: cluster-aodv-nosink.cc → --useSink parametresi ekle
         Test: ./ns3 run "cluster-aodv-nosink --numRegular=30 --numCH=3 --useSink=true"
         Beklenen: Çalışır, sink istatistikleri gösterir

Adım 3: Build & test her ikisini de

Adım 4: run-comparison.sh scripti oluştur (16 simülasyon)

Adım 5: analyze_comparison.py scripti oluştur

Adım 6: Tüm deneyleri çalıştır

Adım 7: Grafikleri üret

Adım 8: Commit & push
```


## 8. BEKLENEN SONUÇLAR

### Deney Seti 1 (Broker'sız) - Beklenti:
```
MQTT-SN daha iyi PDR bekliyoruz çünkü:
  - Heterogeneous trafik (Temp 5s'de bir → az trafik)
  - Priority queue → önemli paketler önce
  - PUBACK → güvenilir teslimat

WSN'de trafik sürekli ve sabit → ağ daha çok yüklenecek
```

### Deney Seti 2 (Broker'lı) - Beklenti:
```
Her ikisinde de PDR düşecek çünkü:
  - CH → Sink trafiği ekstra yük
  - Bottleneck (darboğaz) sink etrafında

MQTT-SN'de priority queue avantajı devam edecek
WSN'de basit forwarding → daha fazla kayıp bekliyoruz
```
