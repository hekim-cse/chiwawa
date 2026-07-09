class AppImages {
  const AppImages._();

  static const mascot = 'assets/images/mascot/chiwawa_mascot.png';
}

class MockImages {
  const MockImages._();

  static const mockPlace01 = 'assets/images/mock/mock_place_01.png';
  static const mockPlace02 = 'assets/images/mock/mock_place_02.png';
  static const mockPlace03 = 'assets/images/mock/mock_place_03.png';
  static const mockMemorial01 = 'assets/images/mock/mock_memorial_01.png';
  static const mockMemorial02 = 'assets/images/mock/mock_memorial_02.png';
  static const mockMemorial03 = 'assets/images/mock/mock_memorial_03.png';

  static const placeImages = [
    mockPlace01,
    mockPlace02,
    mockPlace03,
  ];

  static const memorialImages = [
    mockMemorial01,
    mockMemorial02,
    mockMemorial03,
  ];

  static String placeThumbnail(int seed) {
    return placeImages[seed.abs() % placeImages.length];
  }

  static String memorialPhoto(int index) {
    return memorialImages[index.abs() % memorialImages.length];
  }
}
