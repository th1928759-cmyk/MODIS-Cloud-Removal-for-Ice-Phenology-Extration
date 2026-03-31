// 定义贝加尔湖区域（大致范围）
var baikalRegion = ee.Geometry.Rectangle([103.0, 51.0, 110.0, 56.0]);

// 获取MODIS积雪数据
var dataset = ee.ImageCollection('MODIS/061/MOD10A1')
                  .filter(ee.Filter.date('2019-10-24', '2019-11-01'))
                  .filterBounds(baikalRegion);

// 选择NDSI_Snow_Cover和NDSI_Snow_Cover_Class两个波段
var snowData = dataset.select(['NDSI_Snow_Cover', 'NDSI_Snow_Cover_Class']);

// 可视化参数（针对NDSI_Snow_Cover）
var snowCoverVis = {
  min: 0.0,
  max: 100.0,
  palette: ['black', '0dffff', '0524ff', 'ffffff'],
};

// 设置地图中心（贝加尔湖区域）
Map.setCenter(107.0, 53.5, 6);
Map.addLayer(snowData.select('NDSI_Snow_Cover'), snowCoverVis, 'Snow Cover');

// 导出每日影像
var images = snowData.toList(snowData.size());

// 获取影像数量
var count = images.size().getInfo();

// 循环导出每幅影像
for (var i = 0; i < count; i++) {
  var image = ee.Image(images.get(i));
  
  // 获取影像日期并格式化
  var date = ee.Date(image.get('system:time_start'));
  var dateString = date.format('YYYYMMdd');
  
  // 构建文件名
  var fileName = 'MOD10A1_' + dateString.getInfo();
  
  // 导出设置 - 同时包含两个波段
  Export.image.toDrive({
    image: image.clip(baikalRegion),
    description: fileName,
    fileNamePrefix: fileName,
    region: baikalRegion,
    scale: 500, // MODIS分辨率
    crs: 'EPSG:32648',
    maxPixels: 1e13
  });
}
