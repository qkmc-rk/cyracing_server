from sqlalchemy import (
    Column, Integer, String, ForeignKey, BigInteger, DECIMAL,
    DateTime, Enum, JSON, Index, UniqueConstraint, func
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from .database import Base

# 赛车信息表
class Car(Base):
    __tablename__ = "cars"
    __table_args__ = (
        UniqueConstraint('car_model', name='uk_car_model'),
        {'comment': '赛车信息表'}
    )

    car_id = Column(Integer, primary_key=True, autoincrement=True, comment='赛车ID')
    car_model = Column(String(100), nullable=False, comment='赛车模型名称，如ks_porsche_911_gt3_rs')
    car_name = Column(String(100), nullable=True, comment='赛车显示名称，如保时捷911 GT3 RS')
    manufacturer = Column(String(50), nullable=True, comment='制造商')
    car_class = Column(String(50), nullable=True, comment='赛车级别，如GT3')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')

# 车手信息表
class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint('steam_guid', name='uk_steam_guid'),
        {'comment': '车手信息表'}
    )

    driver_id = Column(Integer, primary_key=True, autoincrement=True, comment='车手ID')
    steam_guid = Column(String(20), nullable=False, comment='Steam GUID，唯一标识')
    driver_name = Column(String(100), nullable=False, comment='车手姓名')
    team_name = Column(String(100), nullable=True, default='', comment='所属车队')
    nation = Column(String(50), nullable=True, default='', comment='国家/地区')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment='更新时间')

# 赛道信息表
class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        UniqueConstraint('track_name', 'track_config', name='uk_track_config'),
        {'comment': '赛道信息表'}
    )

    track_id = Column(Integer, primary_key=True, autoincrement=True, comment='赛道ID')
    track_name = Column(String(100), nullable=False, comment='赛道名称，如spa')
    track_config = Column(String(100), nullable=True, default='', comment='赛道配置，如不同布局')
    country = Column(String(50), nullable=True, comment='赛道所在国家')
    length_km = Column(DECIMAL(5, 3), nullable=True, comment='赛道长度(公里)')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')

# 比赛基本信息表
class Race(Base):
    __tablename__ = "races"
    __table_args__ = (
        UniqueConstraint('source_file', name='uk_source_file'),
        Index('track_id', 'track_id'),
        {'comment': '比赛基本信息表'}
    )

    race_id = Column(Integer, primary_key=True, autoincrement=True, comment='比赛ID')
    track_id = Column(Integer, ForeignKey('tracks.track_id', ondelete='RESTRICT', onupdate='RESTRICT'), 
                      nullable=False, comment='关联赛道ID')
    race_type = Column(Enum('RACE', 'QUALIFY', 'PRACTICE'), nullable=False, comment='比赛类型')
    duration_secs = Column(Integer, nullable=True, default=0, comment='比赛时长(秒)，计时赛使用')
    race_laps = Column(Integer, nullable=True, default=0, comment='比赛圈数，圈数赛使用')
    race_date = Column(DateTime, nullable=False, default=func.now(), comment='比赛日期时间')
    server_name = Column(String(100), nullable=True, comment='服务器名称')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    source_file = Column(String(255), nullable=True, comment='源文件名称')

# 赛事事件表（扩展原有Event模型）
class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index('idx_race_id', 'race_id'),
        Index('idx_driver_id', 'driver_id'),
        Index('idx_event_type', 'event_type'),
        {'comment': '赛事事件表'}
    )

    event_id = Column(BigInteger, primary_key=True, autoincrement=True, comment='事件ID')
    race_id = Column(Integer, ForeignKey('races.race_id', ondelete='CASCADE', onupdate='RESTRICT'), 
                      nullable=False, comment='关联比赛ID')
    event_type = Column(String(50), nullable=False, comment='事件类型')
    driver_id = Column(Integer, nullable=True, comment='关联车手ID')
    car_id = Column(Integer, nullable=True, comment='关联赛车ID')
    session_car_id = Column(Integer, nullable=True, comment='会话内赛车ID')
    other_driver_id = Column(Integer, nullable=True, comment='关联其他车手ID')
    other_car_id = Column(Integer, nullable=True, comment='关联赛车ID')
    impact_speed = Column(DECIMAL(10, 3), nullable=True, comment='碰撞速度')
    world_pos_x = Column(DECIMAL(12, 5), nullable=True, comment='世界坐标X')
    world_pos_y = Column(DECIMAL(12, 5), nullable=True, comment='世界坐标Y')
    world_pos_z = Column(DECIMAL(12, 5), nullable=True, comment='世界坐标Z')
    rel_pos_x = Column(DECIMAL(12, 5), nullable=True, comment='相对坐标X')
    rel_pos_y = Column(DECIMAL(12, 5), nullable=True, comment='相对坐标Y')
    rel_pos_z = Column(DECIMAL(12, 5), nullable=True, comment='相对坐标Z')
    extra_data = Column(JSON, nullable=True, comment='扩展数据')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')

# 单圈详细记录表
class Lap(Base):
    __tablename__ = "laps"
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', 'lap_number', name='uk_race_driver_lap'),
        Index('driver_id', 'driver_id'),
        Index('car_id', 'car_id'),
        {'comment': '单圈详细记录表'}
    )

    lap_id = Column(Integer, primary_key=True, autoincrement=True, comment='单圈ID')
    race_id = Column(Integer, ForeignKey('races.race_id', ondelete='CASCADE', onupdate='RESTRICT'), 
                      nullable=False, comment='关联比赛ID')
    driver_id = Column(Integer, ForeignKey('drivers.driver_id', ondelete='RESTRICT', onupdate='RESTRICT'), 
                      nullable=False, comment='关联车手ID')
    car_id = Column(Integer, ForeignKey('cars.car_id', ondelete='RESTRICT', onupdate='RESTRICT'), 
                      nullable=False, comment='关联赛车ID')
    lap_number = Column(Integer, nullable=False, comment='圈数')
    lap_time_ms = Column(Integer, nullable=False, comment='单圈时间(毫秒)')
    timestamp_ms = Column(BigInteger, nullable=False, comment='圈结束时间戳(毫秒)')
    sector1_ms = Column(Integer, nullable=True, comment='第一分段时间(毫秒)')
    sector2_ms = Column(Integer, nullable=True, comment='第二分段时间(毫秒)')
    sector3_ms = Column(Integer, nullable=True, comment='第三分段时间(毫秒)')
    cuts = Column(Integer, nullable=True, default=0, comment='切弯次数')
    tyre_type = Column(Enum('HR', 'MR', 'SR', 'WET', 'INTER'), nullable=True, comment='轮胎类型')
    ballast_kg = Column(Integer, nullable=True, default=0, comment='本圈配重(千克)')
    restrictor = Column(Integer, nullable=True, default=0, comment='本圈限流器(%)')
    is_valid = Column(TINYINT(1), nullable=True, default=1, comment='是否有效圈')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')

# 比赛最终结果表
class RaceResult(Base):
    __tablename__ = "race_results"
    __table_args__ = (
        UniqueConstraint('race_id', 'driver_id', name='uk_race_driver'),
        Index('driver_id', 'driver_id'),
        Index('car_id', 'car_id'),
        {'comment': '比赛最终结果表'}
    )

    result_id = Column(Integer, primary_key=True, autoincrement=True, comment='结果ID')
    race_id = Column(Integer, ForeignKey('races.race_id', ondelete='CASCADE', onupdate='RESTRICT'), 
                      nullable=False, comment='关联比赛ID')
    driver_id = Column(Integer, ForeignKey('drivers.driver_id', ondelete='RESTRICT', onupdate='RESTRICT'), 
                      nullable=False, comment='关联车手ID')
    car_id = Column(Integer, ForeignKey('cars.car_id', ondelete='RESTRICT', onupdate='RESTRICT'), 
                      nullable=False, comment='关联赛车ID')
    car_skin = Column(String(100), nullable=True, default='', comment='赛车皮肤')
    ballast_kg = Column(Integer, nullable=True, default=0, comment='配重(千克)')
    restrictor = Column(Integer, nullable=True, default=0, comment='限流器(%)')
    best_lap_ms = Column(Integer, nullable=True, comment='最佳单圈时间(毫秒)')
    total_time_ms = Column(BigInteger, nullable=True, default=0, comment='总比赛时间(毫秒)')
    position = Column(Integer, nullable=True, comment='最终排名')
    laps_completed = Column(Integer, nullable=True, default=0, comment='完成圈数')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')

# 用户表（微信小程序绑定）
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint('openid', name='uk_openid'),
        Index('idx_driver_id', 'driver_id'),
        {'comment': '用户表'}
    )

    user_id = Column(Integer, primary_key=True, autoincrement=True, comment='用户主键')
    driver_id = Column(Integer, ForeignKey('drivers.driver_id', ondelete='SET NULL', onupdate='RESTRICT'),
                      nullable=True, comment='关联车手ID')
    openid = Column(String(100), nullable=False, comment='微信openid')
    wechat_name = Column(String(100), nullable=True, comment='微信昵称')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment='更新时间')

# 公告表（富文本公告信息）
class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        Index('idx_is_pinned', 'is_pinned'),
        Index('idx_published_at', 'published_at'),
        {'comment': '公告表'}
    )

    announcement_id = Column(Integer, primary_key=True, autoincrement=True, comment='公告ID')
    title = Column(String(200), nullable=False, comment='公告标题')
    content = Column(JSON, nullable=False, comment='富文本内容（JSON格式，如 Quill Delta）')
    summary = Column(String(500), nullable=True, default='', comment='公告摘要（纯文本）')
    is_pinned = Column(TINYINT(1), nullable=False, default=0, comment='是否置顶：0=否 1=是')
    published_at = Column(DateTime, nullable=True, comment='发布时间')
    created_at = Column(DateTime, nullable=False, default=func.now(), comment='创建时间')
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment='更新时间')

# 车手画像表
class DriverProfile(Base):
    __tablename__ = "driver_profiles"
    __table_args__ = (
        Index('idx_ladder_score', 'ladder_score'),
        {'comment': '车手画像表'}
    )

    profile_id = Column(Integer, primary_key=True, autoincrement=True, comment='画像ID')
    driver_id = Column(Integer, ForeignKey('drivers.driver_id', ondelete='CASCADE', onupdate='RESTRICT'),
                      nullable=False, unique=True, comment='关联车手ID')
    total_races = Column(Integer, nullable=False, default=0, comment='总比赛场次')
    total_laps = Column(Integer, nullable=False, default=0, comment='总驾驶圈数')
    total_drive_time_ms = Column(BigInteger, nullable=False, default=0, comment='总驾驶时间(毫秒)')
    safety_score = Column(DECIMAL(4, 2), nullable=False, default=3.00, comment='安全分，初始3.0')
    ladder_score = Column(Integer, nullable=False, default=1350, comment='天梯分，初始1350')
    license_level = Column(Enum('N', 'D', 'C', 'B', 'A'), nullable=False, default='N', comment='驾照等级')
    rank_overall = Column(Integer, nullable=True, comment='全服排名（按天梯分排序）')
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now(), comment='最后更新时间')

    driver = relationship('Driver', backref='profile')
