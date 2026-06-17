/*
 Navicat Premium Data Transfer

 Source Server         : tank
 Source Server Type    : MySQL
 Source Server Version : 80028
 Source Host           : tanksicau.mysql.rds.aliyuncs.com:3306
 Source Schema         : cyracing

 Target Server Type    : MySQL
 Target Server Version : 80028
 File Encoding         : 65001

 Date: 17/06/2026 14:57:47
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for announcements
-- ----------------------------
DROP TABLE IF EXISTS `announcements`;
CREATE TABLE `announcements`  (
  `announcement_id` int(0) NOT NULL AUTO_INCREMENT COMMENT '公告ID',
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '公告标题',
  `content` json NOT NULL COMMENT '富文本内容（JSON格式，如 Quill Delta）',
  `summary` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '公告摘要（纯文本）',
  `is_pinned` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否置顶：0=否 1=是',
  `published_at` datetime(0) NULL DEFAULT NULL COMMENT '发布时间',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP(0) COMMENT '更新时间',
  PRIMARY KEY (`announcement_id`) USING BTREE,
  INDEX `idx_is_pinned`(`is_pinned`) USING BTREE,
  INDEX `idx_published_at`(`published_at`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '公告表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for cars
-- ----------------------------
DROP TABLE IF EXISTS `cars`;
CREATE TABLE `cars`  (
  `car_id` int(0) NOT NULL AUTO_INCREMENT,
  `car_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '赛车模型名称，如ks_porsche_911_gt3_rs',
  `car_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '赛车显示名称，如保时捷911 GT3 RS',
  `manufacturer` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '制造商',
  `car_class` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '赛车级别，如GT3',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`car_id`) USING BTREE,
  UNIQUE INDEX `uk_car_model`(`car_model`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 2665 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '赛车信息表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for driver_profiles
-- ----------------------------
DROP TABLE IF EXISTS `driver_profiles`;
CREATE TABLE `driver_profiles`  (
  `profile_id` int(0) NOT NULL AUTO_INCREMENT COMMENT '画像ID',
  `driver_id` int(0) NOT NULL COMMENT '关联车手ID',
  `total_races` int(0) NOT NULL DEFAULT 0 COMMENT '总比赛场次',
  `total_laps` int(0) NOT NULL DEFAULT 0 COMMENT '总驾驶圈数',
  `total_drive_time_ms` bigint(0) NOT NULL DEFAULT 0 COMMENT '总驾驶时间(毫秒)',
  `safety_score` decimal(4, 2) NOT NULL DEFAULT 3.00 COMMENT '安全分，初始3.0',
  `ladder_score` int(0) NOT NULL DEFAULT 1350 COMMENT '天梯分，初始1350',
  `license_level` enum('N','D','C','B','A') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL DEFAULT 'N' COMMENT '驾照等级',
  `rank_overall` int(0) NULL DEFAULT NULL COMMENT '全服排名（按天梯分排序）',
  `updated_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP(0) COMMENT '最后更新时间',
  PRIMARY KEY (`profile_id`) USING BTREE,
  UNIQUE INDEX `uk_driver_id`(`driver_id`) USING BTREE,
  INDEX `idx_ladder_score`(`ladder_score`) USING BTREE,
  CONSTRAINT `fk_profile_driver` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 20 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '车手画像表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for drivers
-- ----------------------------
DROP TABLE IF EXISTS `drivers`;
CREATE TABLE `drivers`  (
  `driver_id` int(0) NOT NULL AUTO_INCREMENT,
  `steam_guid` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'Steam GUID，唯一标识',
  `driver_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '车手姓名',
  `team_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '所属车队',
  `nation` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '国家/地区',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP(0),
  PRIMARY KEY (`driver_id`) USING BTREE,
  UNIQUE INDEX `uk_steam_guid`(`steam_guid`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 1075 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '车手信息表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for events
-- ----------------------------
DROP TABLE IF EXISTS `events`;
CREATE TABLE `events`  (
  `event_id` bigint(0) NOT NULL AUTO_INCREMENT,
  `race_id` int(0) NOT NULL,
  `event_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `driver_id` int(0) NULL DEFAULT NULL,
  `car_id` int(0) NULL DEFAULT NULL,
  `session_car_id` int(0) NULL DEFAULT NULL,
  `other_driver_id` int(0) NULL DEFAULT NULL,
  `other_car_id` int(0) NULL DEFAULT NULL,
  `impact_speed` decimal(10, 3) NULL DEFAULT NULL,
  `world_pos_x` decimal(12, 5) NULL DEFAULT NULL,
  `world_pos_y` decimal(12, 5) NULL DEFAULT NULL,
  `world_pos_z` decimal(12, 5) NULL DEFAULT NULL,
  `rel_pos_x` decimal(12, 5) NULL DEFAULT NULL,
  `rel_pos_y` decimal(12, 5) NULL DEFAULT NULL,
  `rel_pos_z` decimal(12, 5) NULL DEFAULT NULL,
  `extra_data` json NULL,
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`event_id`) USING BTREE,
  INDEX `idx_race_id`(`race_id`) USING BTREE,
  INDEX `idx_driver_id`(`driver_id`) USING BTREE,
  INDEX `idx_event_type`(`event_type`) USING BTREE,
  CONSTRAINT `events_ibfk_1` FOREIGN KEY (`race_id`) REFERENCES `races` (`race_id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1066 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for laps
-- ----------------------------
DROP TABLE IF EXISTS `laps`;
CREATE TABLE `laps`  (
  `lap_id` int(0) NOT NULL AUTO_INCREMENT,
  `race_id` int(0) NOT NULL COMMENT '关联比赛ID',
  `driver_id` int(0) NOT NULL COMMENT '关联车手ID',
  `car_id` int(0) NOT NULL COMMENT '关联赛车ID',
  `lap_number` int(0) NOT NULL COMMENT '圈数',
  `lap_time_ms` int(0) NOT NULL COMMENT '单圈时间(毫秒)',
  `timestamp_ms` bigint(0) NOT NULL COMMENT '圈结束时间戳(毫秒)',
  `sector1_ms` int(0) NULL DEFAULT NULL COMMENT '第一分段时间(毫秒)',
  `sector2_ms` int(0) NULL DEFAULT NULL COMMENT '第二分段时间(毫秒)',
  `sector3_ms` int(0) NULL DEFAULT NULL COMMENT '第三分段时间(毫秒)',
  `cuts` int(0) NULL DEFAULT 0 COMMENT '切弯次数',
  `tyre_type` enum('HR','MR','SR','WET','INTER') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '轮胎类型',
  `ballast_kg` int(0) NULL DEFAULT 0 COMMENT '本圈配重(千克)',
  `restrictor` int(0) NULL DEFAULT 0 COMMENT '本圈限流器(%)',
  `is_valid` tinyint(1) NULL DEFAULT 1 COMMENT '是否有效圈',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`lap_id`) USING BTREE,
  UNIQUE INDEX `uk_race_driver_lap`(`race_id`, `driver_id`, `lap_number`) USING BTREE,
  INDEX `driver_id`(`driver_id`) USING BTREE,
  INDEX `car_id`(`car_id`) USING BTREE,
  CONSTRAINT `laps_ibfk_1` FOREIGN KEY (`race_id`) REFERENCES `races` (`race_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `laps_ibfk_2` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `laps_ibfk_3` FOREIGN KEY (`car_id`) REFERENCES `cars` (`car_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 788 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '单圈详细记录表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for race_results
-- ----------------------------
DROP TABLE IF EXISTS `race_results`;
CREATE TABLE `race_results`  (
  `result_id` int(0) NOT NULL AUTO_INCREMENT,
  `race_id` int(0) NOT NULL COMMENT '关联比赛ID',
  `driver_id` int(0) NOT NULL COMMENT '关联车手ID',
  `car_id` int(0) NOT NULL COMMENT '关联赛车ID',
  `car_skin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '赛车皮肤',
  `ballast_kg` int(0) NULL DEFAULT 0 COMMENT '配重(千克)',
  `restrictor` int(0) NULL DEFAULT 0 COMMENT '限流器(%)',
  `best_lap_ms` int(0) NULL DEFAULT NULL COMMENT '最佳单圈时间(毫秒)',
  `total_time_ms` bigint(0) NULL DEFAULT 0 COMMENT '总比赛时间(毫秒)',
  `position` int(0) NULL DEFAULT NULL COMMENT '最终排名',
  `laps_completed` int(0) NULL DEFAULT 0 COMMENT '完成圈数',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`result_id`) USING BTREE,
  UNIQUE INDEX `uk_race_driver`(`race_id`, `driver_id`) USING BTREE,
  INDEX `driver_id`(`driver_id`) USING BTREE,
  INDEX `car_id`(`car_id`) USING BTREE,
  CONSTRAINT `race_results_ibfk_1` FOREIGN KEY (`race_id`) REFERENCES `races` (`race_id`) ON DELETE CASCADE ON UPDATE RESTRICT,
  CONSTRAINT `race_results_ibfk_2` FOREIGN KEY (`driver_id`) REFERENCES `drivers` (`driver_id`) ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT `race_results_ibfk_3` FOREIGN KEY (`car_id`) REFERENCES `cars` (`car_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 1039 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '比赛最终结果表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for races
-- ----------------------------
DROP TABLE IF EXISTS `races`;
CREATE TABLE `races`  (
  `race_id` int(0) NOT NULL AUTO_INCREMENT,
  `track_id` int(0) NOT NULL COMMENT '关联赛道ID',
  `race_type` enum('RACE','QUALIFY','PRACTICE') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '比赛类型',
  `duration_secs` int(0) NULL DEFAULT 0 COMMENT '比赛时长(秒)，计时赛使用',
  `race_laps` int(0) NULL DEFAULT 0 COMMENT '比赛圈数，圈数赛使用',
  `race_date` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '比赛日期时间',
  `server_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '服务器名称',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `source_file` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL,
  PRIMARY KEY (`race_id`) USING BTREE,
  UNIQUE INDEX `uk_source_file`(`source_file`) USING BTREE,
  INDEX `track_id`(`track_id`) USING BTREE,
  CONSTRAINT `races_ibfk_1` FOREIGN KEY (`track_id`) REFERENCES `tracks` (`track_id`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 67 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '比赛基本信息表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for tracks
-- ----------------------------
DROP TABLE IF EXISTS `tracks`;
CREATE TABLE `tracks`  (
  `track_id` int(0) NOT NULL AUTO_INCREMENT,
  `track_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '赛道名称，如spa',
  `track_config` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT '' COMMENT '赛道配置，如不同布局',
  `country` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '赛道所在国家',
  `length_km` decimal(5, 3) NULL DEFAULT NULL COMMENT '赛道长度(公里)',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`track_id`) USING BTREE,
  UNIQUE INDEX `uk_track_config`(`track_name`, `track_config`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 149 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '赛道信息表' ROW_FORMAT = Dynamic;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users`  (
  `user_id` int(0) NOT NULL AUTO_INCREMENT COMMENT '用户主键',
  `driver_id` int(0) NULL DEFAULT NULL COMMENT '关联车手ID',
  `openid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '微信openid',
  `wechat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NULL DEFAULT NULL COMMENT '微信昵称',
  `created_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp(0) NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP(0) COMMENT '更新时间',
  PRIMARY KEY (`user_id`) USING BTREE,
  UNIQUE INDEX `uk_openid`(`openid`) USING BTREE,
  INDEX `idx_driver_id`(`driver_id`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_0900_ai_ci COMMENT = '用户表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
