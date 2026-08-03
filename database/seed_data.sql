-- Display Market Intelligence Agent PoC
-- Synthetic seed data for PostgreSQL.
-- All records are synthetic. No real business data is used.
-- Fact data period: 2022-01-01 to 2026-12-01, 5 years.
-- News data period: 2026-01-01 to 2026-12-01, 1 year.
-- In fact_orders.status, REQUESTED is used as the pending state to match schema.sql.

delete from fact_orders;
delete from fact_sales;
delete from fact_inventory;
delete from market_news;
delete from dim_product;
delete from dim_customer;

insert into dim_customer (
    customer_id,
    customer_name,
    segment,
    region,
    tier,
    main_application
) values
    ('CUST_A', 'Aster Mobile Systems', 'Mobile', 'North America', 'Tier 1', 'Premium smartphone display'),
    ('CUST_B', 'BrightView Electronics', 'TV', 'Europe', 'Tier 1', 'Premium TV display'),
    ('CUST_C', 'CoreIT Devices', 'IT', 'Asia', 'Tier 2', 'Notebook and monitor display'),
    ('CUST_D', 'DrivePanel Mobility', 'Automotive', 'North America', 'Tier 1', 'Automotive cockpit display'),
    ('CUST_E', 'EduTab Labs', 'IT', 'Asia', 'Tier 2', 'Tablet display'),
    ('CUST_F', 'Nova Retail Display', 'TV', 'South America', 'Tier 3', 'Retail and commercial display'),
    ('CUST_G', 'Vertex Phone Labs', 'Mobile', 'Asia', 'Tier 1', 'Foldable smartphone display'),
    ('CUST_H', 'Orion Home Vision', 'TV', 'North America', 'Tier 2', 'Large TV display'),
    ('CUST_I', 'Summit Computing', 'IT', 'Europe', 'Tier 2', 'Notebook display'),
    ('CUST_J', 'Metro Auto UX', 'Automotive', 'Europe', 'Tier 1', 'Infotainment display'),
    ('CUST_K', 'BlueRiver Tablets', 'IT', 'North America', 'Tier 3', 'Education tablet display'),
    ('CUST_L', 'Pioneer Mobility', 'Automotive', 'Asia', 'Tier 2', 'Cluster display'),
    ('CUST_M', 'Zenith Smart Devices', 'Mobile', 'Europe', 'Tier 2', 'Mid-range smartphone display'),
    ('CUST_N', 'Evergreen Signage', 'TV', 'Asia', 'Tier 3', 'Commercial display'),
    ('CUST_O', 'Quantum Workstation', 'IT', 'North America', 'Tier 1', 'Professional monitor display'),
    ('CUST_P', 'Urban EV Systems', 'Automotive', 'South America', 'Tier 2', 'Electric vehicle display'),
    ('CUST_Q', 'Luna Media Hub', 'TV', 'Middle East', 'Tier 2', 'Hospitality TV display'),
    ('CUST_R', 'Atlas Handhelds', 'Mobile', 'South America', 'Tier 3', 'Rugged handheld display'),
    ('CUST_S', 'Helio Learning', 'IT', 'Europe', 'Tier 3', 'Learning device display'),
    ('CUST_T', 'NexMotion Cockpit', 'Automotive', 'North America', 'Tier 1', 'Premium cockpit display'),
    ('CUST_U', 'PixelWave Mobile', 'Mobile', 'Asia', 'Tier 2', 'Gaming smartphone display'),
    ('CUST_V', 'Cedar Office Display', 'IT', 'Middle East', 'Tier 3', 'Office monitor display');

insert into dim_product (
    product_id,
    product_group,
    technology,
    size_inch,
    application
) values
    ('PROD_MOLED_61', 'Mobile OLED', 'OLED', 6.1, 'Smartphone'),
    ('PROD_TOLED_65', 'TV OLED', 'OLED', 65.0, 'Premium TV'),
    ('PROD_IOLED_14', 'IT OLED', 'OLED', 14.0, 'Notebook'),
    ('PROD_AUTO_12', 'Automotive Display', 'OLED', 12.3, 'Vehicle cockpit'),
    ('PROD_LCD_27', 'LCD Monitor', 'LCD', 27.0, 'Desktop monitor'),
    ('PROD_TABLET_11', 'Tablet OLED', 'OLED', 11.0, 'Tablet'),
    ('PROD_MOLED_FOLD', 'Mobile OLED', 'OLED', 7.6, 'Foldable smartphone'),
    ('PROD_LCD_32', 'LCD Monitor', 'LCD', 32.0, 'Large desktop monitor');

insert into fact_sales (
    sales_month,
    customer_id,
    product_id,
    qty,
    revenue,
    asp
)
select
    m.sales_month,
    c.customer_id,
    p.product_id,
    cast(round(
        base.base_qty
        * c.customer_weight
        * (
            case
                when p.product_group = 'Mobile OLED' then 1.00 + (m.month_seq * 0.018)
                when p.product_group = 'TV OLED' and m.sales_month < date '2026-04-01' then 1.00 + (m.month_seq * 0.006)
                when p.product_group = 'TV OLED' then 1.30 - ((m.month_seq - 51) * 0.010)
                when p.product_group = 'LCD Monitor' then 1.10 - (m.month_seq * 0.010)
                when p.product_group = 'IT OLED' and m.sales_month = date '2026-05-01' then 2.35
                when p.product_group = 'IT OLED' then 1.00 + (m.month_seq * 0.010)
                when p.product_group = 'Automotive Display' then 1.00 + (m.month_seq * 0.012)
                when p.product_group = 'Tablet OLED' then 1.00 + (m.month_seq * 0.009)
                else 1.00
            end
        )
        * (
            case
                when c.customer_id in ('CUST_A', 'CUST_D', 'CUST_G', 'CUST_T') and m.sales_month >= date '2026-05-01' then 1.25
                when c.customer_id in ('CUST_C', 'CUST_O') and m.sales_month >= date '2026-05-01' then 1.45
                else 1.00
            end
        )
    ) as integer) as qty,
    cast(round(
        cast(round(
            base.base_qty
            * c.customer_weight
            * (
                case
                    when p.product_group = 'Mobile OLED' then 1.00 + (m.month_seq * 0.018)
                    when p.product_group = 'TV OLED' and m.sales_month < date '2026-04-01' then 1.00 + (m.month_seq * 0.006)
                    when p.product_group = 'TV OLED' then 1.30 - ((m.month_seq - 51) * 0.010)
                    when p.product_group = 'LCD Monitor' then 1.10 - (m.month_seq * 0.010)
                    when p.product_group = 'IT OLED' and m.sales_month = date '2026-05-01' then 2.35
                    when p.product_group = 'IT OLED' then 1.00 + (m.month_seq * 0.010)
                    when p.product_group = 'Automotive Display' then 1.00 + (m.month_seq * 0.012)
                    when p.product_group = 'Tablet OLED' then 1.00 + (m.month_seq * 0.009)
                    else 1.00
                end
            )
            * (
                case
                    when c.customer_id in ('CUST_A', 'CUST_D', 'CUST_G', 'CUST_T') and m.sales_month >= date '2026-05-01' then 1.25
                    when c.customer_id in ('CUST_C', 'CUST_O') and m.sales_month >= date '2026-05-01' then 1.45
                    else 1.00
                end
            )
        ) as numeric)
        * (base.base_asp * (1.00 - (m.month_seq * 0.0025))), 2
    ) as numeric(18, 2)) as revenue,
    cast(round(base.base_asp * (1.00 - (m.month_seq * 0.0025)), 2) as numeric(18, 2)) as asp
from (
    select
        cast(gs.sales_month as date) as sales_month,
        row_number() over (order by gs.sales_month) - 1 as month_seq
    from generate_series(date '2022-01-01', date '2026-12-01', interval '1 month') as gs(sales_month)
) m
join (
    values
        ('CUST_A', 'PROD_MOLED_61', 1.20),
        ('CUST_G', 'PROD_MOLED_FOLD', 1.10),
        ('CUST_M', 'PROD_MOLED_61', 0.85),
        ('CUST_R', 'PROD_MOLED_61', 0.60),
        ('CUST_U', 'PROD_MOLED_FOLD', 0.90),
        ('CUST_B', 'PROD_TOLED_65', 1.15),
        ('CUST_H', 'PROD_TOLED_65', 0.90),
        ('CUST_F', 'PROD_TOLED_65', 0.70),
        ('CUST_N', 'PROD_TOLED_65', 0.55),
        ('CUST_Q', 'PROD_TOLED_65', 0.65),
        ('CUST_C', 'PROD_IOLED_14', 1.00),
        ('CUST_I', 'PROD_IOLED_14', 0.80),
        ('CUST_O', 'PROD_LCD_32', 0.95),
        ('CUST_S', 'PROD_TABLET_11', 0.60),
        ('CUST_K', 'PROD_TABLET_11', 0.75),
        ('CUST_E', 'PROD_TABLET_11', 0.85),
        ('CUST_D', 'PROD_AUTO_12', 1.05),
        ('CUST_J', 'PROD_AUTO_12', 0.90),
        ('CUST_L', 'PROD_AUTO_12', 0.70),
        ('CUST_P', 'PROD_AUTO_12', 0.65),
        ('CUST_T', 'PROD_AUTO_12', 1.10),
        ('CUST_V', 'PROD_LCD_27', 0.70),
        ('CUST_C', 'PROD_LCD_27', 0.90),
        ('CUST_O', 'PROD_LCD_27', 0.75)
) c(customer_id, product_id, customer_weight)
join dim_product p on p.product_id = c.product_id
join (
    values
        ('Mobile OLED', 8000, 95.00),
        ('TV OLED', 2500, 720.00),
        ('IT OLED', 1800, 310.00),
        ('Automotive Display', 1100, 470.00),
        ('LCD Monitor', 6500, 165.00),
        ('Tablet OLED', 2600, 235.00)
) base(product_group, base_qty, base_asp) on base.product_group = p.product_group;

insert into fact_orders (
    order_date,
    customer_id,
    product_id,
    order_qty,
    requested_delivery_date,
    confirmed_delivery_date,
    status
)
select
    cast(m.order_month + ((o.order_day_offset || ' days')::interval) as date) as order_date,
    o.customer_id,
    o.product_id,
    cast(round(o.base_order_qty * (
        case
            when o.customer_id in ('CUST_A', 'CUST_D', 'CUST_G', 'CUST_T') and m.order_month >= date '2026-05-01' then 1.60
            when o.customer_id in ('CUST_C', 'CUST_O') and m.order_month >= date '2026-05-01' then 1.80
            when p.product_group = 'LCD Monitor' then 1.20 - (m.month_seq * 0.010)
            else 1.00 + (m.month_seq * 0.008)
        end
    )) as integer) as order_qty,
    cast(m.order_month + interval '45 days' as date) as requested_delivery_date,
    case
        when s.status in ('REQUESTED', 'CANCELLED') then null
        when s.status = 'DELAYED' then cast(m.order_month + interval '58 days' as date)
        else cast(m.order_month + interval '43 days' as date)
    end as confirmed_delivery_date,
    s.status
from (
    select
        cast(gs.order_month as date) as order_month,
        row_number() over (order by gs.order_month) - 1 as month_seq
    from generate_series(date '2022-01-01', date '2026-12-01', interval '1 month') as gs(order_month)
) m
join (
    values
        (1, 'CUST_A', 'PROD_MOLED_61', 12000, 5),
        (2, 'CUST_B', 'PROD_TOLED_65', 3300, 8),
        (3, 'CUST_C', 'PROD_IOLED_14', 2800, 11),
        (4, 'CUST_D', 'PROD_AUTO_12', 1700, 14),
        (5, 'CUST_O', 'PROD_LCD_32', 5200, 17),
        (6, 'CUST_E', 'PROD_TABLET_11', 3600, 20)
) o(order_slot, customer_id, product_id, base_order_qty, order_day_offset) on true
join dim_product p on p.product_id = o.product_id
join (
    values
        (0, 'CONFIRMED'),
        (1, 'REQUESTED'),
        (2, 'DELAYED'),
        (3, 'CONFIRMED'),
        (4, 'SHIPPED'),
        (5, 'CANCELLED')
) s(status_key, status) on s.status_key = ((m.month_seq + o.order_slot) % 6);

insert into fact_inventory (
    inventory_month,
    product_id,
    beginning_stock,
    production_qty,
    sales_qty,
    ending_stock,
    safety_stock
)
select
    x.inventory_month,
    x.product_id,
    x.beginning_stock,
    x.production_qty,
    x.sales_qty,
    x.ending_stock,
    x.safety_stock
from (
    select
        m.inventory_month,
        p.product_id,
        cast(round(inv.base_stock * (
            case
                when p.product_group = 'Mobile OLED' then 1.25 - (m.month_seq * 0.010)
                when p.product_group = 'TV OLED' and m.inventory_month >= date '2026-04-01' then 1.20 + ((m.month_seq - 51) * 0.080)
                when p.product_group = 'LCD Monitor' then 1.10 + (m.month_seq * 0.018)
                when p.product_group = 'IT OLED' and m.inventory_month = date '2026-06-01' then 0.85
                else 1.00 + (m.month_seq * 0.003)
            end
        )) as integer) as beginning_stock,
        cast(round(inv.base_production * (
            case
                when p.product_group = 'TV OLED' and m.inventory_month >= date '2026-04-01' then 1.35
                when p.product_group = 'LCD Monitor' then 1.08
                else 1.00
            end
        )) as integer) as production_qty,
        cast(round(inv.base_sales * (
            case
                when p.product_group = 'Mobile OLED' then 1.05
                when p.product_group = 'LCD Monitor' then 0.95
                else 1.00
            end
        )) as integer) as sales_qty,
        cast(round(
            (inv.base_stock * (
                case
                    when p.product_group = 'Mobile OLED' then 1.25 - (m.month_seq * 0.010)
                    when p.product_group = 'TV OLED' and m.inventory_month >= date '2026-04-01' then 1.20 + ((m.month_seq - 51) * 0.080)
                    when p.product_group = 'LCD Monitor' then 1.10 + (m.month_seq * 0.018)
                    when p.product_group = 'IT OLED' and m.inventory_month = date '2026-06-01' then 0.85
                    else 1.00 + (m.month_seq * 0.003)
                end
            ))
            + (inv.base_production * (
                case
                    when p.product_group = 'TV OLED' and m.inventory_month >= date '2026-04-01' then 1.35
                    when p.product_group = 'LCD Monitor' then 1.08
                    else 1.00
                end
            ))
            - (inv.base_sales * (
                case
                    when p.product_group = 'Mobile OLED' then 1.05
                    when p.product_group = 'LCD Monitor' then 0.95
                    else 1.00
                end
            ))
        ) as integer) as ending_stock,
        inv.safety_stock
    from (
        select
            cast(gs.inventory_month as date) as inventory_month,
            row_number() over (order by gs.inventory_month) - 1 as month_seq
        from generate_series(date '2022-01-01', date '2026-12-01', interval '1 month') as gs(inventory_month)
    ) m
    join dim_product p on true
    join (
        values
            ('Mobile OLED', 26000, 10500, 12000, 18000),
            ('TV OLED', 8500, 4200, 3600, 5000),
            ('IT OLED', 6200, 2500, 2300, 3500),
            ('Automotive Display', 4300, 1600, 1400, 2500),
            ('LCD Monitor', 14000, 7200, 6100, 6000),
            ('Tablet OLED', 6800, 3300, 3100, 3200)
    ) inv(product_group, base_stock, base_production, base_sales, safety_stock)
        on inv.product_group = p.product_group
    left join (
        select
            sales_month,
            product_id,
            sum(qty) as sales_qty
        from fact_sales
        group by sales_month, product_id
    ) s on s.sales_month = m.inventory_month
        and s.product_id = p.product_id
) x
where x.ending_stock >= 0;

insert into market_news (
    news_date,
    company,
    category,
    title,
    summary,
    impact_score,
    related_product_group
) values
    ('2026-01-08', 'BOE', 'capacity', 'BOE expands mid-size OLED preparation plan', 'BOE announced a synthetic capacity expansion scenario for mid-size OLED panels, increasing competitive pressure in IT OLED.', 4, 'IT OLED'),
    ('2026-01-24', 'CSOT', 'price', 'CSOT starts regional LCD monitor price campaign', 'CSOT launched a synthetic price promotion for LCD monitor panels, adding downside pressure to ASP.', 3, 'LCD Monitor'),
    ('2026-02-10', 'SDC', 'technology', 'SDC highlights low-power mobile OLED roadmap', 'SDC introduced a synthetic low-power OLED roadmap that may influence premium smartphone display requirements.', 4, 'Mobile OLED'),
    ('2026-02-25', 'LGD', 'investment', 'LGD reviews automotive OLED investment option', 'LGD disclosed a synthetic investment review for automotive cockpit display capacity.', 3, 'Automotive Display'),
    ('2026-03-09', 'BOE', 'customer', 'BOE targets new tablet display customers', 'BOE increased synthetic customer engagement for tablet OLED supply in Asia.', 3, 'Tablet OLED'),
    ('2026-03-21', 'CSOT', 'capacity', 'CSOT adds LCD monitor back-end capacity', 'CSOT synthetic back-end capacity movement may worsen LCD monitor oversupply risk.', 4, 'LCD Monitor'),
    ('2026-04-06', 'CSOT', 'capacity', 'CSOT increases TV OLED pilot output', 'CSOT synthetic pilot output increased after April, creating potential supply competition in TV OLED.', 4, 'TV OLED'),
    ('2026-04-22', 'LGD', 'price', 'LGD signals selective TV OLED price adjustment', 'LGD synthetic pricing update suggests cautious demand after April for premium TV OLED.', 4, 'TV OLED'),
    ('2026-05-07', 'SDC', 'technology', 'SDC promotes hybrid OLED for notebook panels', 'SDC synthetic technology messaging strengthened market interest in IT OLED, matching a May demand spike.', 5, 'IT OLED'),
    ('2026-05-19', 'BOE', 'investment', 'BOE accelerates mobile OLED yield improvement program', 'BOE synthetic yield improvement plan may increase supply availability for mobile OLED panels.', 4, 'Mobile OLED'),
    ('2026-06-04', 'CSOT', 'customer', 'CSOT wins synthetic automotive display design-in', 'CSOT announced a synthetic automotive display design-in that may affect future cockpit display competition.', 3, 'Automotive Display'),
    ('2026-06-18', 'LGD', 'capacity', 'LGD adjusts TV OLED utilization plan', 'LGD synthetic utilization adjustment points to slower TV OLED demand and higher channel inventory risk.', 5, 'TV OLED'),
    ('2026-07-08', 'SDC', 'price', 'SDC offers strategic tablet OLED bundle proposal', 'SDC synthetic bundle proposal may create price pressure for tablet OLED negotiations.', 3, 'Tablet OLED'),
    ('2026-07-23', 'BOE', 'technology', 'BOE previews oxide backplane improvement', 'BOE synthetic technology update may support thinner IT OLED panels.', 3, 'IT OLED'),
    ('2026-08-11', 'LGD', 'customer', 'LGD strengthens premium TV customer program', 'LGD synthetic customer program may intensify competition for high-end TV accounts.', 4, 'TV OLED'),
    ('2026-08-27', 'CSOT', 'investment', 'CSOT reviews automotive display module line', 'CSOT synthetic investment review signals interest in automotive cockpit display modules.', 3, 'Automotive Display'),
    ('2026-09-09', 'SDC', 'capacity', 'SDC optimizes mobile OLED fab allocation', 'SDC synthetic fab allocation may shift supply toward premium mobile OLED panels.', 4, 'Mobile OLED'),
    ('2026-09-26', 'BOE', 'price', 'BOE tests aggressive notebook OLED quote', 'BOE synthetic notebook OLED quote may increase pricing pressure in IT OLED.', 4, 'IT OLED'),
    ('2026-10-07', 'LGD', 'technology', 'LGD showcases brighter TV OLED stack', 'LGD synthetic TV OLED stack update may improve premium segment differentiation.', 5, 'TV OLED'),
    ('2026-10-23', 'CSOT', 'customer', 'CSOT expands monitor customer sampling', 'CSOT synthetic monitor sampling may accelerate LCD monitor price competition.', 3, 'LCD Monitor'),
    ('2026-11-06', 'BOE', 'capacity', 'BOE schedules tablet OLED ramp scenario', 'BOE synthetic ramp scenario could increase tablet OLED supply from early next year.', 4, 'Tablet OLED'),
    ('2026-11-20', 'SDC', 'investment', 'SDC evaluates automotive OLED reliability line', 'SDC synthetic reliability investment may strengthen automotive display qualification.', 3, 'Automotive Display'),
    ('2026-12-05', 'LGD', 'price', 'LGD reviews year-end TV OLED pricing', 'LGD synthetic year-end pricing review reflects soft TV OLED demand and inventory pressure.', 4, 'TV OLED'),
    ('2026-12-18', 'BOE', 'technology', 'BOE announces synthetic foldable OLED improvement', 'BOE synthetic foldable OLED progress may increase competition in mobile OLED design wins.', 5, 'Mobile OLED');

-- Validation queries
select count(*) as customer_count
from dim_customer;

select count(*) as product_count
from dim_product;

select
    'fact_sales' as table_name,
    min(sales_month) as min_date,
    max(sales_month) as max_date,
    count(*) as row_count
from fact_sales
union all
select
    'fact_orders' as table_name,
    min(order_date) as min_date,
    max(order_date) as max_date,
    count(*) as row_count
from fact_orders
union all
select
    'fact_inventory' as table_name,
    min(inventory_month) as min_date,
    max(inventory_month) as max_date,
    count(*) as row_count
from fact_inventory;

select
    p.product_group,
    s.sales_month,
    sum(s.qty) as total_qty,
    sum(s.revenue) as total_revenue,
    round(avg(s.asp), 2) as avg_asp
from fact_sales s
join dim_product p on p.product_id = s.product_id
where s.sales_month between date '2026-01-01' and date '2026-06-01'
group by p.product_group, s.sales_month
order by p.product_group, s.sales_month;

select
    status,
    count(*) as order_count,
    sum(order_qty) as total_order_qty
from fact_orders
group by status
order by status;

select
    p.product_group,
    i.inventory_month,
    i.ending_stock,
    i.safety_stock,
    case
        when i.ending_stock < i.safety_stock then 'BELOW_SAFETY_STOCK'
        when i.ending_stock > i.safety_stock * 2 then 'OVER_STOCK'
        else 'NORMAL'
    end as inventory_signal
from fact_inventory i
join dim_product p on p.product_id = i.product_id
where i.inventory_month = date '2026-06-01'
order by p.product_group, p.product_id;

select
    category,
    count(*) as news_count,
    avg(impact_score) as avg_impact_score
from market_news
group by category
order by category;
