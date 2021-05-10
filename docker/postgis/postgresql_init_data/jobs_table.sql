create table if not exists jobs (
	id serial primary key,
	minx double precision not null,
	miny double precision not null,
	maxx double precision not null,
	maxy double precision not null,
	data_id varchar,
	status varchar(10)
);

