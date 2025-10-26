# PowerPack Controller R2M1 - v2.0.0

## 📋 Genel Bakış

Bu uygulama, HW_BO_POWERPACK_R2M1 kartını USB CDC üzerinden kontrol etmek için kullanılır.

## ✨ Özellikler

- **2 Bağımsız Röle Kontrolü** (GPIO_M1 ve GPIO_M2)
- **2 Kanal Dimmer Kontrolü** (0-10V çıkış, GP8413 DAC)
- **USB CDC İletişimi**
- **Durum İzleme**
- **Grafik Kullanıcı Arayüzü (GUI)**
- **Heartbeat LED Göstergesi**

## 🚀 Nasıl Kullanılır?

### Adım 1: Donanım Bağlantısı
1. STM32 kartınızı USB kablosuyla bilgisayara bağlayın
2. Windows, cihazı otomatik olarak tanımalıdır (STM32 Virtual COM Port)

### Adım 2: Uygulamayı Çalıştırın
1. `PowerPack_Controller_R2M1_v2.0.0.exe` dosyasını çift tıklayarak çalıştırın
2. Hiçbir ek kurulum gerekmez - standalone exe dosyasıdır

### Adım 3: Bağlantı
1. **USB Port** açılır menüsünden doğru COM portunu seçin
2. **"Connect"** butonuna tıklayın
3. Bağlantı başarılıysa yeşil LED yanıp sönmeye başlar

### Adım 4: Kontrol
- **Röle 1 ve Röle 2:** ON/OFF checkbox'larını kullanarak kontrol edin
- **Dimmer 1 ve Dimmer 2:** 
  - "Enable" checkbox ile aktifleştirin
  - Slider ile %0-100 arası ayarlayın

### Ek Butonlar
- **Get Status:** Cihazdan durum bilgisi al
- **Get Version:** Firmware versiyonunu öğren
- **Debug Test:** USB iletişim testi yap
- **All OFF:** Tüm çıkışları kapat
- **Test Sequence:** Otomatik test dizisi çalıştır

## 📊 Teknik Bilgiler

### Donanım Özellikleri
- **MCU:** STM32F103C8T6
- **Röle Kontrolü:** 
  - Röle 1: GPIO_M1 (PB13)
  - Röle 2: GPIO_M2 (PB12)
- **Dimmer Kontrolü:**
  - DAC: GP8413 (I2C)
  - Çıkış: 0-10V analog
  - Enable 1: DIM_OUT_EN_1 (PB0)
  - Enable 2: DIM_OUT_EN_2 (PB1)
- **İletişim:** USB CDC (Virtual COM Port)

### Yazılım Özellikleri
- **Python Versiyon:** v2.0.0
- **Firmware Versiyon:** v2.0.0
- **İletişim Protokolü:**
  - Baud Rate: 115200
  - Data Bits: 8
  - Parity: None
  - Stop Bits: 1

## 🔧 Sorun Giderme

### "Bağlantı Başarısız" Hatası
1. USB kablosunun düzgün bağlı olduğundan emin olun
2. Doğru COM portunu seçtiğinizden emin olun
3. Başka bir program COM portunu kullanıyor olabilir - kapatın
4. Cihazı çıkarıp tekrar takın

### "Cihaz Bulunamadı" Hatası
1. STM32 USB sürücüsünün yüklü olduğundan emin olun
2. Windows Cihaz Yöneticisi'nde COM portunu kontrol edin
3. Firmware'in cihaza yüklendiğinden emin olun

### Röleler Çalışmıyor
1. Güç kaynağının bağlı olduğundan emin olun
2. "Get Status" ile röle durumunu kontrol edin
3. Her iki röle de bağımsız çalışır - ikisini de test edin

### Dimmer Çıkışı Yok
1. "Enable" checkbox'ının işaretli olduğundan emin olun
2. Slider değerinin %0'dan farklı olduğundan emin olun
3. 0-10V çıkış voltajını multimetre ile ölçün

## 📝 Komut Satırı Kullanımı

Gelişmiş kullanıcılar için CLI modu:

```bash
PowerPack_Controller_R2M1_v2.0.0.exe --cli
```

Kullanılabilir komutlar:
- `connect_usb [port]` - USB'den bağlan
- `relay <1|2> <on|off>` - Röle kontrolü
- `dimmer <1|2> <0-100>` - Dimmer yüzdesi ayarla
- `enable_dimmer <1|2>` - Dimmer'ı aktifleştir
- `disable_dimmer <1|2>` - Dimmer'ı devre dışı bırak
- `status` - Durum bilgisi al
- `version` - Versiyon bilgisi al
- `quit` - Çıkış

## ⚠️ Uyumluluk

**Önemli:** Bu versiyon sadece R2M1 donanımı ile uyumludur!

- ✅ **Uyumlu:** HW_BO_POWERPACK_R2M1 + Firmware v2.0.0
- ❌ **Uyumsuz:** HW_BO_POWERPACK_R1M1 + Firmware v1.0.0

R1M1 ve R2M1 arasındaki farklar:
- **R1M1:** 1 adet latching röle (SET/RESET kontrol)
- **R2M1:** 2 adet bağımsız röle (direkt kontrol)

## 📞 Destek

Sorun yaşarsanız:
1. Durum penceresindeki mesajları kontrol edin
2. "Debug Test" ile iletişimi test edin
3. Cihazı yeniden başlatın (çıkar-tak)
4. Uygulamayı kapatıp yeniden açın

## 📄 Lisans

© 2025 BlackOcean Technologies
Tüm hakları saklıdır.

---

**Son Güncelleme:** 25 Ekim 2025  
**Versiyon:** 2.0.0  
**Donanım:** R2M1


