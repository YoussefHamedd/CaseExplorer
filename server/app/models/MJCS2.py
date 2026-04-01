from .common import TableBase, MetaColumn as Column, CaseTable
from sqlalchemy import Date, Numeric, Integer, String, Boolean, ForeignKey, Index, Text, BigInteger
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr


class MJCS2(CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2'
    is_root = True

    id = Column(Integer, primary_key=True)
    internal_id = Column(String)
    court_system = Column(String)
    case_category = Column(String, enum=True)
    case_type = Column(String, enum=True)
    case_title = Column(String)
    filing_date = Column(Date)
    _filing_date_str = Column('filing_date_str', String)
    case_status = Column(String, enum=True)
    case_status_date = Column(Date)
    court_name = Column(String, enum=True)
    judge_assigned = Column(String, enum=True)
    charge_track_number = Column(String)
    violation_date = Column(Date)
    violation_county = Column(String, enum=True)

    case = relationship('Case', backref=backref('mjcs2', uselist=False))

    __table_args__ = (
        Index('ixh_mjcs2_case_number', 'case_number', postgresql_using='hash'),
    )


class MJCS2CaseTable(CaseTable):
    @declared_attr
    def case_number(self):
        return Column(String, ForeignKey('mjcs2.case_number', ondelete='CASCADE'), nullable=False)


class MJCS2Defendant(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_defendants'
    __table_args__ = (Index('ixh_mjcs2_defendants_case_number', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='defendants')

    id = Column(Integer, primary_key=True)
    defendant_name = Column(String)
    race = Column(String, enum=True)
    gender = Column(String, enum=True)
    dob = Column(String)
    height_feet = Column(Integer)
    height_inches = Column(Integer)
    weight = Column(Integer)
    address_line1 = Column(String)
    address_line2 = Column(String)
    city = Column(String, enum=True)
    state = Column(String, enum=True)
    zip = Column(String, enum=True)
    current_address = Column(Boolean)


class MJCS2InvolvedParty(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_involved_parties'
    __table_args__ = (Index('ixh_mjcs2_involved_parties_case_number', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='involved_parties')

    id = Column(Integer, primary_key=True)
    party_type = Column(String, enum=True)
    party_name = Column(String)
    address_line1 = Column(String)
    address_line2 = Column(String)
    city = Column(String, enum=True)
    state = Column(String, enum=True)
    zip = Column(String, enum=True)


class MJCS2Attorney(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_attorneys'
    __table_args__ = (Index('ixh_mjcs2_attorneys_case_number', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='attorneys')

    id = Column(Integer, primary_key=True)
    party_name = Column(String)
    attorney_name = Column(String)
    appearance_date = Column(Date)
    address_line1 = Column(String)
    city = Column(String, enum=True)
    state = Column(String, enum=True)
    zip = Column(String, enum=True)


class MJCS2Charge(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_charges'
    __table_args__ = (Index('ixh_mjcs2_charges_cn', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='charges')

    id = Column(Integer, primary_key=True)
    charge_number = Column(Integer)
    statute_code = Column(String)
    charge_description = Column(String)
    offense_date = Column(Date)
    fine_amount = Column(Numeric)
    officer_name = Column(String, enum=True)
    agency_name = Column(String, enum=True)
    vehicle_tag = Column(String)
    vehicle_desc = Column(String)
    recorded_speed = Column(Integer)
    speed_limit = Column(Integer)
    mandatory_court = Column(String)
    probable_cause = Column(String)
    disposition = Column(String, enum=True)


class MJCS2Hearing(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_hearings'
    __table_args__ = (Index('ixh_mjcs2_hearings_cn', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='hearings')

    id = Column(Integer, primary_key=True)
    event_type = Column(String, enum=True)
    event_date = Column(Date)
    event_time = Column(String)
    location = Column(String, enum=True)
    room = Column(String, enum=True)
    result = Column(Text)
    judge = Column(String, enum=True)


class MJCS2Event(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_events'
    __table_args__ = (Index('ixh_mjcs2_events_case_number', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='events')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date)
    document_name = Column(String)
    internal_event_id = Column(BigInteger)


class MJCS2Judgment(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_judgments'
    __table_args__ = (Index('ixh_mjcs2_judgments_case_number', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='judgments')

    id = Column(Integer, primary_key=True)
    judgment_type = Column(String, enum=True)
    issue_date = Column(Date)
    judge = Column(String, enum=True)


class MJCS2ServiceEvent(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_service_events'
    __table_args__ = (Index('ixh_mjcs2_se_cn', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='service_events')

    id = Column(Integer, primary_key=True)
    service_type = Column(String, enum=True)
    issue_date = Column(Date)


class MJCS2Cause(MJCS2CaseTable, TableBase):
    '''Maryland Court Cases (New API)'''
    __tablename__ = 'mjcs2_causes'
    __table_args__ = (Index('ixh_mjcs2_causes_cn', 'case_number', postgresql_using='hash'),)
    mjcs2 = relationship('MJCS2', backref='causes')

    id = Column(Integer, primary_key=True)
    file_date = Column(Date)
    filed_by = Column(String, enum=True)
    filed_against = Column(String, enum=True)
    cause_description = Column(String)
    remedy = Column(String, enum=True)
    remedy_amount = Column(Numeric)
    remedy_comment = Column(Text)
