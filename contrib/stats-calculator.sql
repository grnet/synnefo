# Top level
create temporary table tmp_stats as select 0 as "level", 0 as "node", 0 as "parent", count(serial) as "population", sum(size) as "bytes", max(mtime) as "mtime", cluster, false as "final" from versions group by cluster;

# Account level
insert into tmp_stats select 1 as "level", n.node, n.parent, count(v.serial) as "population", sum(v.size) as "bytes", max(v.mtime) as "mtime", cluster, false as "final" from versions v, nodes n where n.node=v.node and n.parent=0 and n.node!=0 group by node, cluster;
create temporary table tmp_nodes select distinct node, level from tmp_stats where level=1;

# Container level
insert into tmp_stats select 2 as "level", n.node, n.parent, count(v.serial) as "population", sum(v.size) as "bytes", max(v.mtime) as "mtime", cluster, false as "final" from versions v, nodes n where n.node=v.node and n.parent in (select node from tmp_nodes where level=1) group by node, cluster;
insert into tmp_nodes select distinct node, level from tmp_stats where level=2;

# Object level
insert into tmp_stats select 3 as "level", n.node, n.parent, count(v.serial) as "population", sum(v.size) as "bytes", max(v.mtime) as "mtime", cluster, false as "final" from versions v, nodes n where n.node=v.node and n.parent in (select node from tmp_nodes where level=2) group by node, cluster;
insert into tmp_nodes select distinct node, level from tmp_stats where level=3;

# Update containers
create table tmp_sums as select parent as "node", sum(population) as "population", sum(bytes) as "bytes", max(mtime) as "mtime", cluster from tmp_stats where level=3 group by parent, cluster;
insert into tmp_stats select 2 as "level", n.node, n.parent, t.population, t.bytes, t.mtime, t.cluster, true as "final" from tmp_sums t, nodes n where n.node=t.node;
drop table tmp_sums;

# Update accounts
create table tmp_sums as select parent as "node", sum(bytes) as "bytes", max(mtime) as "mtime", cluster from tmp_stats where level=2 group by parent, cluster;
create table tmp_population as select parent as "node", sum(population) as "population", cluster from tmp_stats where level=2 and final=false group by parent, cluster;
insert into tmp_stats select 1 as "level", t.node, 0 as "parent", IFNULL(p.population, 0) as "population", t.bytes, t.mtime, t.cluster, true as "final" from tmp_sums t left join tmp_population p on p.node=t.node and p.cluster=t.cluster;
drop table tmp_sums;
drop table tmp_population;

# Update top level
create table tmp_sums as select parent as "node", sum(bytes) as "bytes", max(mtime) as "mtime", cluster from tmp_stats where level=1 group by parent, cluster;
create table tmp_population as select parent as "node", sum(population) as "population", cluster from tmp_stats where level=1 and final=false group by parent, cluster;
insert into tmp_stats select 0 as "level", t.node, 0 as "parent", IFNULL(p.population, 0) as "population", t.bytes, t.mtime, t.cluster, true as "final" from tmp_sums t left join tmp_population p on p.node=t.node and p.cluster=t.cluster;
drop table tmp_sums;
drop table tmp_population;

# Clean up
drop table tmp_nodes;
delete from tmp_stats where final=false;
