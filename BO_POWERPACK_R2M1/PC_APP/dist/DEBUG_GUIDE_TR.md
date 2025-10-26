# PowerPack R2M1 - Debug Versiyonu

## 🐛 Debug Özellikleri

Bu versiyon, PowerPack R2M1'in Python uygulaması ve STM32 firmware'inde kapsamlı debug özellikleri içerir.

## 🔍 Python Uygulaması Debug Özellikleri

### 1. Debug Console Penceresi
- **Siyah arka plan, yeşil yazı** ile profesyonel görünüm
- Tüm log mesajlarını **gerçek zamanlı** gösterir
- Son 500 satır otomatik saklanır
- "Clear Console" butonu ile temizlenebilir

### 2. Detaylı Connection Logging
```
=== USB Connection Attempt to COM3 ===
Serial port opened: COM3
Buffers cleared
Waiting 3 seconds for device to stabilize...
Bytes waiting after stabilization: 128
*** Received boot data (128 bytes): b'...'
*** Boot data hex: 3d3d3d205...
=== Connection established to COM3 ===
```

### 3. is_connected() Debug
- Serial port durumu
- Son haberleşme zamanı
- Aktif/pasif durumu
```
is_connected: Port open, last_comm=1.2s ago, active=True
```

### 4. Status Monitor Thread Logging
```
=== Status monitor thread started ===
Sending periodic status request...
✓ Got response: status
```

## 🔍 STM32 Firmware Debug Özellikleri

### 1. Boot Messages
Cihaz başlatıldığında USB CDC üzerinden şu mesajlar gönderilir:
```
=== PowerPack R2M1 v2.0.0 Started ===
System Clock: 48 MHz
Initializing PowerPack...
PowerPack initialized successfully
Relay 1: OFF, Relay 2: OFF
Ready for commands!
```

### 2. Command Logging
Her gelen komut loglanır:
```
RX: 8 bytes [ 01 01 00 00 00 00 00 00 ]
CMD: 0x01, param: 1, value: 0
Relay 1 -> ON
```

### 3. Unknown Command Detection
```
CMD: 0xFF, param: 0, value: 0
Unknown command: 0xFF
```

## 📊 Nasıl Kullanılır?

### Adım 1: Debug Exe'yi Çalıştır
```
PowerPack_Controller_R2M1_v2.0.0_DEBUG.exe
```

### Adım 2: Console'u İzle
- Alt kısımda **Debug Console** penceresi açılır
- Yeşil yazılar ile tüm log mesajları görünür

### Adım 3: Bağlantıyı Test Et
1. COM port seçin
2. "Connect" butonuna tıklayın
3. Console'da şunları göreceksiniz:
   ```
   22:17:38 [INFO] === USB Connection Attempt to COM3 ===
   22:17:38 [INFO] Serial port opened: COM3
   22:17:38 [INFO] Buffers cleared
   22:17:38 [INFO] Waiting 3 seconds for device to stabilize...
   22:17:41 [INFO] Bytes waiting after stabilization: 0
   22:17:41 [WARNING] !!! No boot message received from device !!!
   22:17:41 [INFO] === Connection established to COM3 ===
   22:17:41 [INFO] === Status monitor thread started ===
   ```

### Adım 4: Boot Message Kontrolü
Eğer **"No boot message received"** görüyorsanız:
- ❌ STM32'de kod YOK veya çalışmıyor
- ❌ Firmware yüklenmemiş
- ❌ USB CDC başlatılmamış

Eğer boot message görüyorsanız:
- ✅ STM32 çalışıyor
- ✅ Firmware aktif
- ✅ USB CDC çalışıyor
- ✅ Haberleşme mevcut

## 🎯 Sorun Tespiti

### Senaryo 1: LED Yeşil Ama Boot Message Yok
```
[INFO] Bytes waiting after stabilization: 0
[WARNING] !!! No boot message received from device !!!
[DEBUG] is_connected: Port open, last_comm=0.0s ago, active=True
```
**Sonuç:** Serial port açık ama cihaz cevap vermiyor → **STM32'de kod yok!**

### Senaryo 2: Boot Message Var, Status Geliyor
```
[INFO] *** Received boot data (128 bytes): ...
[INFO] ✓ Got response: status
[DEBUG] is_connected: Port open, last_comm=0.1s ago, active=True
```
**Sonuç:** Her şey çalışıyor → **Haberleşme OK!**

### Senaryo 3: Boot Message Var, Sonra Sessizlik
```
[INFO] *** Received boot data (128 bytes): ...
[DEBUG] Sending periodic status request...
[DEBUG] is_connected: Port open, last_comm=3.2s ago, active=True
[DEBUG] is_connected: Port open, last_comm=5.3s ago, active=False
```
**Sonuç:** Başlangıçta çalıştı, sonra durdu → **Firmware crash veya USB hatası**

## 🔧 Debug Komutları

### "Debug Test" Butonu
Python'dan raw komutlar gönderir:
```
[INFO] 🔧 Debug Test: Sending raw version command...
[INFO] 🔧 Sent raw bytes: ['0xa', '0x0', '0x0', '0x0', '0x0', '0x0', '0x0', '0x0']
[INFO] 🔧 Received bytes: ['0xa', '0x2', '0x0', '0x0']
```

### "Get Version" Butonu
Firmware versiyonunu ister:
```
[DEBUG] Sending command: 0x0A (param=0, value=0)
[INFO] ✓ Got response: version
[INFO] 📋 Firmware version: v2.0.0
```

## 📝 Log Seviyeleri

- **[DEBUG]**: Detaylı debug bilgisi
- **[INFO]**: Genel bilgi mesajları  
- **[WARNING]**: Uyarı mesajları
- **[ERROR]**: Hata mesajları

## 💡 İpuçları

1. **Console'u temizleyin**: Çok fazla log birikirse "Clear Console" kullanın
2. **Boot message'ı bekleyin**: Connect'ten sonra 3 saniye bekleyin
3. **Tekrar bağlanın**: Sorun varsa Disconnect → Connect yapın
4. **STM32'yi reset edin**: Reset tuşuna basıp yeni boot message alın

## 🚀 Sonraki Adımlar

1. Debug exe'yi çalıştırın
2. COM port seçin ve bağlanın
3. Console'da boot message'ı kontrol edin
4. Eğer boot message geliyorsa → **Haberleşme OK**
5. Eğer boot message gelmiyorsa → **STM32'ye kod yükleyin**

---

**Debug Versiyon:** v2.0.0_DEBUG  
**Oluşturulma:** 25 Ekim 2025  
**Amaç:** Haberleşme problemlerini tespit etmek

