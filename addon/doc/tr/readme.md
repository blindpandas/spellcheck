# Yazım Denetimi  

- yazarlar: Fawaz Abdulrahman<fawaz.ar94@gmail.com> ve  
- Musharraf Omer<ibnomer2011@hotmail.com>  
- sürüm: 1.1
- İndir: [Kararlı Sürüm:][1]  

## Hakkında:  

Eklentinin amacı metindeki yazım hatalarını hızlı bir şekilde bulup düzeltebilmemize imkan sağlamaktır.  
Ayrıca, Sözlükte bulunmayan kelimeleri ekleyebileceğiniz kişisel bir kelime listesi de oluşturabilirsiniz.  

## Kullanım:  

- Denetlemek istediğiniz metnin tümünü CTRL+A ile seçmeli veya dilediğiniz bir kısmını diğer seçme yöntemleri ile seçmelisiniz.  
- Eklenti arayüzünü çağırmak için NVDA+Alt+s tuşlarına basın.  
- Yazım denetimi varsayılan yazma dilinize göre yapılacaktır.  
- Alternatif olarak, NVDA+ALT+SHIFT+L tuşlarına basarak açılacak listeden dilediğiniz dili seçebilirsiniz.  
- hata yoksa yazım hatası olmadığını belirten bir mesaj duyurusu yapılır.  
- hata olması durumunda, yanlış yazılan kelimeler arasında gezinmek için sağ ve sol yön tuşlarını, Öneri listesini açmak için Enter veya aşağı yön tuşunu kullanın.  
- Öneri listesinde Aşağı ve yukarı yön tuşları ile gezebilir, dilediğiniz öneriyi seçtikten sonra Enter tuşu ile ilgili öneriyi uygulayabilirsiniz. Sağ ve Sol yön tuşları ile hatalı kelimeler arasında gezinirken, NVDA öneri listesinden seçtiğimiz kelimeyi de seslendirecektir.  
- Sağ ve sol yön tuşları ile hatalar arasında gezinirken, seçilen bir öneriyi kaldırmak için Geri Silme(Back Space) tuşuna basabilirsiniz.  
- Bittiğinde, vurgulanan metinde seçilen önerileri değiştirmek için Control + r tuşlarına basın.  
- Control+r, sözcükleri değiştirmeye ek olarak, bu seçeneği işaretlediyseniz sözcüğü kişisel sözlüğe de ekler.  

### kişisel sözlük:

öneriler menüsünde, kelimeyi kişisel sözlüğe ekleme seçeneği vardır. Benzer bir yazım yanlışı kelimesini bir daha aradığınızda, kişisel sözlük kelimeleri, normal sözlüğe ek olarak öneriler listesinde görünecektir.  
Örneğin, kişisel sözlüğe "Fawaz" kelimesini eklerseniz, bir dahaki sefere "Fawz" yazdığınızda "Fawaz" gösterilen öneriler arasında bulunur.  
Kişisel sözlüğe eklenen herhangi bir kelimeyi, NVDA'nın kullanıcı yapılandırma klasöründeki yazım denetimi_dic klasöründe bulunan (dil etiketi) dosyasını (dil etiketi) düzenleyerek kaldırabilirsiniz.  
Bu, kurulu sürüm appdata/roaming/nvda ve taşınabilir sürüm kullanıcı yapılandırma klasörü içindir.  
ABD İngilizcesi için dosya adı en_US.dic olacaktır.  

### Bu defa yok say:  

Hata listesinde bulunan bir kelimeyi, öneri listesinin en sondan ikinci seçeneği olan "Bu defa yok say" seçeneğini kullanarak bu defalık bu şekilde kalmasını sağlayabilirsiniz.
örneğin: "merhaba nvda kullanıcıları, nvda ve eklentileriyle harika vakit geçireceğinizi umuyoruz. Şüphesiz, nvda harika bir ekran okuyucudur.", Metninde üç hata bulunur. Eğer NVDA kelimesi için "Bu defa yok Say" seçeneğini kullanırsak, Hata sayısı sıfıra düşecek ve hiç hata bulunmayacaktır.  

## Diğer diller için destek:

Eklenti, varsayılan olarak, eklentiyi yüklerken izninizle yüklenecek olan İngilizce sözlükle birlikte gelir.  
Yazım denetimi, varsayılan klavye giriş diline bağlı olarak yapılacaktır.  
Ancak, sözlük önceden yüklenmemişse, NVDA sizden o dilin sözlüğünü yüklemenizi isteyecektir.  
Evet'e tıkladığınızda, sözlük yüklenecek ve varsayılan klavye dilinde denetim yapılacaktır.  
Ek olarak, bir dili manuel olarak seçebileceğiniz ve daha önce indirilmemişse sözlüğü indirebileceğiniz veya o dilde yazım denetimi yapabileceğiniz dillerin listesini getirmek için NVDA+ALT+SHIFT+L tuşlarına basabilirsiniz.  
Varsayılan klavye diline dönmek için aynı kısa yol tuşlarına tekrar basabilirsiniz.  

## notlar

- Escape tuşuna basarsanız, yapılan deyişiklikler kaydedilmeden pencereden çıkılacaktır.  
- Herhangi bir metni değiştirmeden sadece kişisel sözlüğe kelime eklemek isteseniz bile, bu kelimelerin kişisel sözlüğe eklenmesi için control+r tuşlarına basmanız gerekir.  
- Yazım denetleme kısa yolu olan (NVDA+alt+s), Kaydetme kısayol tuşu (kontrol+r) ve manuel dil seçim kısayol tuşu olan (NVDA+Alt+SHIFT+L) seçeneklerini Girdi hreketleri iletişim kutusundan değiştirebilirsiniz.  


## klavye kısayolları:

- NVDA+alt+s: Eklentiyi etkinleştirir. (Giriş hareketlerinden değiştirilebilir).  
-Sağ ve Sol yön tuşları: Bulunan Yazım hataları arasında dolaşmamızı sağlar.  
- Enter veya Aşağı yön tuşu: Öneri listesini açar.  
- Yukarı ve aşağı yön tuşu: öneriler arasında gezinmemizi sağlar.  
- enter: üzerinde bulunan öneriyi seçer.  
- backspace: Seçilen bir öneriyi kaldırır.
- Ctrl + c: düzeltilmiş metni seçili metni değiştirmeden panoya kopyalamak için. (Giriş hareketlerinden değiştirilebilir).  
- control + r: metin alanında seçilen önerileri değiştirmek için  kullanılır. (Giriş hareketlerinden değiştirilebilir).  
- Escape: Hem öneriler menüsünü hem de yanlış yazılmış sözcükler menüsünü kapatır.  
- NVDA+Alt+SHIFT+L: Farklı diller seçebileceğimiz bir liste açar. (giriş hareketlerinden değiştirilebilir).  

[1]: https://github.com/blindpandas/spellcheck/releases/download/v1.1/spellcheck-1.1.nvda-addon