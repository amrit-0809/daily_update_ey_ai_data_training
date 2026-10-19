-- CREATE TABLE suppliers (
--     supplier_id INT PRIMARY KEY,
--     supplier_name VARCHAR(100),
--     city VARCHAR(50)
-- );

-- CREATE TABLE parts (
--     part_id INT PRIMARY KEY,
--     part_name VARCHAR(100),
--     category VARCHAR(50),
--     unit_price DECIMAL(10,2),
--     stock_qty INT
-- );

-- CREATE TABLE purchase_orders (
--     po_id INT PRIMARY KEY,
--     supplier_id INT REFERENCES suppliers(supplier_id),
--     order_date DATE,
--     status VARCHAR(30)
-- );

-- CREATE TABLE purchase_order_items (
--     po_item_id INT PRIMARY KEY,
--     po_id INT REFERENCES purchase_orders(po_id),
--     part_id INT REFERENCES parts(part_id),
--     quantity INT
-- );

-- INSERT INTO suppliers VALUES
-- (1,'Axis Components','Rajkot'),
-- (2,'Prime Industrial','Pune'),
-- (3,'Nova Engineering','Coimbatore'),
-- (4,'Delta Supply Works','Bhubaneswar'),
-- (5,'Mektron Systems','Nashik'),
-- (6,'Cobalt Traders','Surat');

-- INSERT INTO parts VALUES
-- (101,'Bearing Set','Mechanical',1250,38),
-- (102,'Control Relay','Electrical',850,60),
-- (103,'Hydraulic Seal','Mechanical',420,95),
-- (104,'Temperature Sensor','Electronics',1850,24),
-- (105,'Drive Belt','Mechanical',760,42),
-- (106,'PLC Module','Electronics',5400,10),
-- (107,'Fuse Pack','Electrical',290,120);

-- INSERT INTO purchase_orders VALUES
-- (1001,1,'2026-10-01','Received'),
-- (1002,2,'2026-10-02','Pending'),
-- (1003,3,'2026-10-03','Received'),
-- (1004,1,'2026-10-05','Pending'),
-- (1005,5,'2026-10-06','Cancelled');

-- INSERT INTO purchase_order_items VALUES
-- (1,1001,101,10),
-- (2,1001,103,20),
-- (3,1002,102,15),
-- (4,1002,104,6),
-- (5,1003,105,12),
-- (6,1003,107,30),
-- (7,1004,106,2),
-- (8,1005,103,10);

select * from parts where category='Mechanical'
----------------------------------------------------2
select * from parts where unit_price>1000 order by unit_price desc
--------------------------------------------------------------------3
select category , avg(unit_price) from parts group by category
----------------------------------------------------------------------4
select category, sum(stock_qty) from parts group by category
----------------------------------------------------------------------5
select s.supplier_name,po.order_date,po.status
from purchase_orders po
join suppliers s on po.supplier_id=s.supplier_id
--------------------------------------------------------------------6
select po.po_id,p.part_name,poi.quantity,p.unit_price
from purchase_orders po
join purchase_order_items poi on po.po_id=poi.po_id
join parts p on poi.part_id=p.part_id
------------------------------------------------------------7
select po.po_id,p.part_name,poi.quantity,p.unit_price,(poi.quantity*p.unit_price) as line_total
from purchase_orders po
join purchase_order_items poi on po.po_id=poi.po_id
join parts p on poi.part_id=p.part_id
------------------------------------------------------------8
select * from suppliers s
left join purchase_orders po on s.supplier_id=po.supplier_id
---------------------------------------------------------------9
select s.* from suppliers s
left join purchase_orders po on s.supplier_id=po.supplier_id
where po.po_id is null
---------------------------------------------------------------10
create view purchase_order_summary as
select po.po_id, s.supplier_name, p.part_name, poi.quantity, p.unit_price,(poi.quantity*p.unit_price) as line_total
from purchase_orders po
join suppliers s on po.supplier_id=s.supplier_id
join purchase_order_items poi on po.po_id=poi.po_id
join parts p on poi.part_id=p.part_id
--------------------------------------------------------------------11
create or replace function calculate_part_discount(amount numeric)
returns numeric as $$
begin
	if amount>=2000 then
		return amount*0.10;
	else
		return 0;
	end if;
end;
$$ LANGUAGE plpgsql
--------------------------------------------------------------------12
create or replace function final_part_price(amount numeric)
returns numeric as $$
begin
	return amount- calculate_part_discount(amount);
end;
$$ language plpgsql;

select part_name, unit_price, final_part_price(unit_price) as discounted_price from parts
-----------------------------------------------------------------------------------------------13
create or replace procedure update_po_status(p_po_id int, p_new_status varchar) as $$
Begin
	update purchase_orders set status= p_new_status where po_id=p_po_id;
end;
$$language plpgsql;
----------------------------------------------------------------------------------------14
create or replace procedure mark_old_pending_orders() as $$
begin
	update purcahse_orders
	set status='Received'
	where status='Pending' and order_date<'2026-10-04';
end;
$$ language plpgsql;
-------------------------------------------------------------------15
-- Supplier Details ( supplier_name, supplier_city,) and part details (part_name and part_ category) will duplicate across
-- rows when they are stored in an single flat table.
-- we can normalize them into supplier_name, part_name,purchase_orders and purchase_order_items which are further linked via
-- forign keys such as supplier_id , part_id and po_id.
