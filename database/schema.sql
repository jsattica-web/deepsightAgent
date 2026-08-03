-- Display Market Intelligence Agent PoC
-- PostgreSQL schema for Synthetic Data only.
-- ML demand forecasting is intentionally excluded from this schema.

drop table if exists fact_orders cascade;
drop table if exists fact_sales cascade;
drop table if exists fact_inventory cascade;
drop table if exists market_news cascade;
drop table if exists dim_product cascade;
drop table if exists dim_customer cascade;

create table dim_customer (
    customer_id varchar(30) primary key,
    customer_name varchar(100) not null,
    segment varchar(50) not null,
    region varchar(50) not null,
    tier varchar(20) not null,
    main_application varchar(100) not null
);

create table dim_product (
    product_id varchar(30) primary key,
    product_group varchar(50) not null,
    technology varchar(50) not null,
    size_inch numeric(5, 1) not null,
    application varchar(100) not null
);

create table fact_sales (
    sales_id bigserial primary key,
    sales_month date not null,
    customer_id varchar(30) not null,
    product_id varchar(30) not null,
    qty integer not null,
    revenue numeric(18, 2) not null,
    asp numeric(18, 2) not null,
    constraint fk_fact_sales_customer
        foreign key (customer_id)
        references dim_customer (customer_id),
    constraint fk_fact_sales_product
        foreign key (product_id)
        references dim_product (product_id),
    constraint ck_fact_sales_qty
        check (qty >= 0),
    constraint ck_fact_sales_revenue
        check (revenue >= 0),
    constraint ck_fact_sales_asp
        check (asp >= 0)
);

create table fact_orders (
    order_id bigserial primary key,
    order_date date not null,
    customer_id varchar(30) not null,
    product_id varchar(30) not null,
    order_qty integer not null,
    requested_delivery_date date not null,
    confirmed_delivery_date date,
    status varchar(30) not null,
    constraint fk_fact_orders_customer
        foreign key (customer_id)
        references dim_customer (customer_id),
    constraint fk_fact_orders_product
        foreign key (product_id)
        references dim_product (product_id),
    constraint ck_fact_orders_qty
        check (order_qty >= 0),
    constraint ck_fact_orders_status
        check (status in ('REQUESTED', 'CONFIRMED', 'DELAYED', 'SHIPPED', 'CANCELLED'))
);

create table fact_inventory (
    inventory_id bigserial primary key,
    inventory_month date not null,
    product_id varchar(30) not null,
    beginning_stock integer not null,
    production_qty integer not null,
    sales_qty integer not null,
    ending_stock integer not null,
    safety_stock integer not null,
    constraint fk_fact_inventory_product
        foreign key (product_id)
        references dim_product (product_id),
    constraint ck_fact_inventory_beginning_stock
        check (beginning_stock >= 0),
    constraint ck_fact_inventory_production_qty
        check (production_qty >= 0),
    constraint ck_fact_inventory_sales_qty
        check (sales_qty >= 0),
    constraint ck_fact_inventory_ending_stock
        check (ending_stock >= 0),
    constraint ck_fact_inventory_safety_stock
        check (safety_stock >= 0)
);

create table market_news (
    news_id bigserial primary key,
    news_date date not null,
    company varchar(100) not null,
    category varchar(50) not null,
    title varchar(200) not null,
    summary text not null,
    impact_score numeric(5, 2) not null,
    related_product_group varchar(50) not null,
    constraint ck_market_news_impact_score
        check (impact_score >= 0 and impact_score <= 100)
);

comment on table dim_customer is 'Synthetic 고객사 차원 테이블';
comment on column dim_customer.customer_id is '고객사 식별자';
comment on column dim_customer.customer_name is 'Synthetic 고객사명';
comment on column dim_customer.segment is '고객사 세그먼트';
comment on column dim_customer.region is '고객사 주요 지역';
comment on column dim_customer.tier is '고객사 등급';
comment on column dim_customer.main_application is '고객사의 주요 디스플레이 적용 분야';

comment on table dim_product is 'Synthetic 제품 차원 테이블';
comment on column dim_product.product_id is '제품 식별자';
comment on column dim_product.product_group is '제품군';
comment on column dim_product.technology is '디스플레이 기술 유형';
comment on column dim_product.size_inch is '제품 크기. 단위는 inch';
comment on column dim_product.application is '제품 적용 분야';

comment on table fact_sales is 'Synthetic 판매 실적 팩트 테이블';
comment on column fact_sales.sales_id is '판매 실적 식별자';
comment on column fact_sales.sales_month is '판매 기준 월. 월 단위 데이터이며 해당 월의 1일 사용';
comment on column fact_sales.customer_id is '고객사 식별자. dim_customer 참조';
comment on column fact_sales.product_id is '제품 식별자. dim_product 참조';
comment on column fact_sales.qty is '판매 수량';
comment on column fact_sales.revenue is '판매 금액';
comment on column fact_sales.asp is '평균 판매 단가. Average Selling Price';

comment on table fact_orders is 'Synthetic 수주 팩트 테이블';
comment on column fact_orders.order_id is '수주 식별자';
comment on column fact_orders.order_date is '수주 접수일';
comment on column fact_orders.customer_id is '고객사 식별자. dim_customer 참조';
comment on column fact_orders.product_id is '제품 식별자. dim_product 참조';
comment on column fact_orders.order_qty is '수주 수량';
comment on column fact_orders.requested_delivery_date is '고객 요청 납기일';
comment on column fact_orders.confirmed_delivery_date is '확정 납기일';
comment on column fact_orders.status is '수주 상태. REQUESTED, CONFIRMED, DELAYED, SHIPPED, CANCELLED';

comment on table fact_inventory is 'Synthetic 재고 팩트 테이블';
comment on column fact_inventory.inventory_id is '재고 식별자';
comment on column fact_inventory.inventory_month is '재고 기준 월. 월 단위 데이터이며 해당 월의 1일 사용';
comment on column fact_inventory.product_id is '제품 식별자. dim_product 참조';
comment on column fact_inventory.beginning_stock is '월초 재고 수량';
comment on column fact_inventory.production_qty is '월간 생산 수량';
comment on column fact_inventory.sales_qty is '월간 판매 또는 출하 수량';
comment on column fact_inventory.ending_stock is '월말 재고 수량';
comment on column fact_inventory.safety_stock is '안전 재고 수량';

comment on table market_news is 'Synthetic 경쟁사 및 시장 뉴스 테이블';
comment on column market_news.news_id is '뉴스 식별자';
comment on column market_news.news_date is '뉴스 발생일';
comment on column market_news.company is 'Synthetic 회사명 또는 경쟁사명';
comment on column market_news.category is '뉴스 분류';
comment on column market_news.title is '뉴스 제목';
comment on column market_news.summary is '뉴스 요약';
comment on column market_news.impact_score is '시장 영향 점수. 0에서 100 사이 값';
comment on column market_news.related_product_group is '관련 제품군';

create index idx_dim_customer_region
    on dim_customer (region);

create index idx_dim_customer_segment
    on dim_customer (segment);

create index idx_dim_customer_tier
    on dim_customer (tier);

create index idx_dim_product_group
    on dim_product (product_group);

create index idx_dim_product_technology
    on dim_product (technology);

create index idx_fact_sales_month
    on fact_sales (sales_month);

create index idx_fact_sales_customer_month
    on fact_sales (customer_id, sales_month);

create index idx_fact_sales_product_month
    on fact_sales (product_id, sales_month);

create index idx_fact_orders_order_date
    on fact_orders (order_date);

create index idx_fact_orders_customer_date
    on fact_orders (customer_id, order_date);

create index idx_fact_orders_product_date
    on fact_orders (product_id, order_date);

create index idx_fact_orders_status
    on fact_orders (status);

create index idx_fact_inventory_month
    on fact_inventory (inventory_month);

create index idx_fact_inventory_product_month
    on fact_inventory (product_id, inventory_month);

create index idx_market_news_date
    on market_news (news_date);

create index idx_market_news_company
    on market_news (company);

create index idx_market_news_category
    on market_news (category);

create index idx_market_news_product_group
    on market_news (related_product_group);
