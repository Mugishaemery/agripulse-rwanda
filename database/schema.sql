-- PROVISIONAL schema. Finalise after inspecting the real NISR microdata values.
CREATE DATABASE IF NOT EXISTS agripulse CHARACTER SET utf8mb4;
USE agripulse;
CREATE TABLE districts (id INT AUTO_INCREMENT PRIMARY KEY, province VARCHAR(40) NOT NULL, district_name VARCHAR(60) NOT NULL UNIQUE, district_code VARCHAR(10));
CREATE TABLE crops (id INT AUTO_INCREMENT PRIMARY KEY, crop_code VARCHAR(20), crop_name VARCHAR(80) NOT NULL UNIQUE);
CREATE TABLE agricultural_records (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  district_id INT NOT NULL, crop_id INT NOT NULL,
  season ENUM('A','B','C') NOT NULL,
  plot_area_sqm DECIMAL(12,2) NOT NULL,          -- s2q2
  production_kg DECIMAL(14,2),                   -- s2q21/s2q22 (to confirm)
  yield_kg_ha DECIMAL(12,2),                     -- production_kg / (plot_area_sqm/10000)
  improved_seed BOOLEAN, fertilizer_organic BOOLEAN, fertilizer_inorganic BOOLEAN, pesticide BOOLEAN,
  erosion_degree VARCHAR(20), anti_erosion BOOLEAN, consolidated_land BOOLEAN,
  mechanized BOOLEAN, irrigated BOOLEAN, plot_weight DOUBLE,
  FOREIGN KEY (district_id) REFERENCES districts(id), FOREIGN KEY (crop_id) REFERENCES crops(id),
  INDEX idx_dcs (district_id, crop_id, season)
);
CREATE TABLE model_runs (id INT AUTO_INCREMENT PRIMARY KEY, model_name VARCHAR(60), mae DOUBLE, rmse DOUBLE, r2 DOUBLE, trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, feature_importance JSON);
