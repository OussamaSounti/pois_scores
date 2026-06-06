--
-- PostgreSQL database dump
--

\restrict iW3BAQoJhYBPiuWBQIEPwSX6Kc1rBA8Sde0dOTgRSKLmfvyl2ZzmZfiEEtKRA6O

-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: active; Type: SCHEMA; Schema: -; Owner: poi_user
--

CREATE SCHEMA active;


ALTER SCHEMA active OWNER TO poi_user;

--
-- Name: geo; Type: SCHEMA; Schema: -; Owner: poi_user
--

CREATE SCHEMA geo;


ALTER SCHEMA geo OWNER TO poi_user;

--
-- Name: history; Type: SCHEMA; Schema: -; Owner: poi_user
--

CREATE SCHEMA history;


ALTER SCHEMA history OWNER TO poi_user;

--
-- Name: production; Type: SCHEMA; Schema: -; Owner: poi_user
--

CREATE SCHEMA production;


ALTER SCHEMA production OWNER TO poi_user;

--
-- Name: tiger; Type: SCHEMA; Schema: -; Owner: poi_user
--

CREATE SCHEMA tiger;


ALTER SCHEMA tiger OWNER TO poi_user;

--
-- Name: topology; Type: SCHEMA; Schema: -; Owner: poi_user
--

CREATE SCHEMA topology;


ALTER SCHEMA topology OWNER TO poi_user;

--
-- Name: SCHEMA topology; Type: COMMENT; Schema: -; Owner: poi_user
--

COMMENT ON SCHEMA topology IS 'PostGIS Topology schema';


--
-- Name: fuzzystrmatch; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA public;


--
-- Name: EXTENSION fuzzystrmatch; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION fuzzystrmatch IS 'determine similarities and distance between strings';


--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


--
-- Name: postgis_tiger_geocoder; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder WITH SCHEMA tiger;


--
-- Name: EXTENSION postgis_tiger_geocoder; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_tiger_geocoder IS 'PostGIS tiger geocoder and reverse geocoder';


--
-- Name: postgis_topology; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis_topology WITH SCHEMA topology;


--
-- Name: EXTENSION postgis_topology; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis_topology IS 'PostGIS topology spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_pipeline_runs; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.audit_pipeline_runs (
    run_id integer NOT NULL,
    run_timestamp timestamp with time zone DEFAULT now() NOT NULL,
    source_file text,
    source_snapshot_date date,
    pipeline_version text,
    status text DEFAULT 'running'::text NOT NULL,
    duration_seconds double precision,
    notes text,
    mode character varying,
    error_message text
);


ALTER TABLE active.audit_pipeline_runs OWNER TO poi_user;

--
-- Name: audit_pipeline_runs_run_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.audit_pipeline_runs_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.audit_pipeline_runs_run_id_seq OWNER TO poi_user;

--
-- Name: audit_pipeline_runs_run_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.audit_pipeline_runs_run_id_seq OWNED BY active.audit_pipeline_runs.run_id;


--
-- Name: audit_pois_history; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.audit_pois_history (
    id bigint NOT NULL,
    run_id integer NOT NULL,
    osm_id text NOT NULL,
    change_type text NOT NULL,
    name text,
    fclass text,
    super_category text,
    latitude double precision,
    longitude double precision,
    geom public.geometry(Point,4326),
    content_hash text,
    valid_from timestamp with time zone,
    valid_to timestamp with time zone
);


ALTER TABLE active.audit_pois_history OWNER TO poi_user;

--
-- Name: audit_pois_history_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.audit_pois_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.audit_pois_history_id_seq OWNER TO poi_user;

--
-- Name: audit_pois_history_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.audit_pois_history_id_seq OWNED BY active.audit_pois_history.id;


--
-- Name: audit_run_stats; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.audit_run_stats (
    run_id integer NOT NULL,
    total_raw integer,
    total_after_filter integer,
    inserted integer,
    updated integer,
    deactivated integer,
    reactivated integer,
    unchanged integer
);


ALTER TABLE active.audit_run_stats OWNER TO poi_user;

--
-- Name: categories; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.categories (
    id integer NOT NULL,
    name character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE active.categories OWNER TO poi_user;

--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.categories_id_seq OWNER TO poi_user;

--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.categories_id_seq OWNED BY active.categories.id;


--
-- Name: category_mapping; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.category_mapping (
    id integer NOT NULL,
    category_id integer NOT NULL,
    fclass character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE active.category_mapping OWNER TO poi_user;

--
-- Name: category_mapping_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.category_mapping_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.category_mapping_id_seq OWNER TO poi_user;

--
-- Name: category_mapping_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.category_mapping_id_seq OWNED BY active.category_mapping.id;


--
-- Name: city_polygons; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.city_polygons (
    id integer NOT NULL,
    name text,
    fclass text,
    geom public.geometry(MultiPolygon,4326)
);


ALTER TABLE active.city_polygons OWNER TO poi_user;

--
-- Name: city_polygons_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.city_polygons_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.city_polygons_id_seq OWNER TO poi_user;

--
-- Name: city_polygons_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.city_polygons_id_seq OWNED BY active.city_polygons.id;


--
-- Name: inspection_log; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.inspection_log (
    id bigint NOT NULL,
    logged_at timestamp with time zone DEFAULT now() NOT NULL,
    fclass character varying NOT NULL,
    action character varying NOT NULL,
    mode character varying,
    detail text
);


ALTER TABLE active.inspection_log OWNER TO poi_user;

--
-- Name: inspection_log_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.inspection_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.inspection_log_id_seq OWNER TO poi_user;

--
-- Name: inspection_log_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.inspection_log_id_seq OWNED BY active.inspection_log.id;


--
-- Name: production_pois_current; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.production_pois_current (
    id bigint NOT NULL,
    osm_id text NOT NULL,
    name text DEFAULT 'Unnamed'::text NOT NULL,
    fclass text NOT NULL,
    super_category text NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    geom public.geometry(Point,4326),
    content_hash text NOT NULL,
    first_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    source_snapshot_date date
);


ALTER TABLE active.production_pois_current OWNER TO poi_user;

--
-- Name: production_pois_current_id_seq; Type: SEQUENCE; Schema: active; Owner: poi_user
--

CREATE SEQUENCE active.production_pois_current_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE active.production_pois_current_id_seq OWNER TO poi_user;

--
-- Name: production_pois_current_id_seq; Type: SEQUENCE OWNED BY; Schema: active; Owner: poi_user
--

ALTER SEQUENCE active.production_pois_current_id_seq OWNED BY active.production_pois_current.id;


--
-- Name: staging_pois_stage; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.staging_pois_stage (
    osm_id text,
    name text,
    fclass text,
    super_category text,
    latitude double precision,
    longitude double precision,
    geom public.geometry(Point,4326),
    content_hash text
);


ALTER TABLE active.staging_pois_stage OWNER TO poi_user;

--
-- Name: staging_raw_pois; Type: TABLE; Schema: active; Owner: poi_user
--

CREATE TABLE active.staging_raw_pois (
    osm_id text,
    name text,
    fclass text,
    latitude double precision,
    longitude double precision,
    geom public.geometry(Point,4326),
    source_layer text
);


ALTER TABLE active.staging_raw_pois OWNER TO poi_user;

--
-- Name: coastline; Type: TABLE; Schema: geo; Owner: poi_user
--

CREATE TABLE geo.coastline (
    id integer NOT NULL,
    name text,
    geom public.geometry(MultiLineString,4326)
);


ALTER TABLE geo.coastline OWNER TO poi_user;

--
-- Name: coastline_id_seq; Type: SEQUENCE; Schema: geo; Owner: poi_user
--

CREATE SEQUENCE geo.coastline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE geo.coastline_id_seq OWNER TO poi_user;

--
-- Name: coastline_id_seq; Type: SEQUENCE OWNED BY; Schema: geo; Owner: poi_user
--

ALTER SEQUENCE geo.coastline_id_seq OWNED BY geo.coastline.id;


--
-- Name: land; Type: TABLE; Schema: geo; Owner: poi_user
--

CREATE TABLE geo.land (
    id integer NOT NULL,
    name text,
    geom public.geometry(MultiPolygon,4326)
);


ALTER TABLE geo.land OWNER TO poi_user;

--
-- Name: land_id_seq; Type: SEQUENCE; Schema: geo; Owner: poi_user
--

CREATE SEQUENCE geo.land_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE geo.land_id_seq OWNER TO poi_user;

--
-- Name: land_id_seq; Type: SEQUENCE OWNED BY; Schema: geo; Owner: poi_user
--

ALTER SEQUENCE geo.land_id_seq OWNED BY geo.land.id;


--
-- Name: audit_pipeline_runs; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.audit_pipeline_runs (
    run_id integer NOT NULL,
    run_timestamp timestamp with time zone DEFAULT now() NOT NULL,
    source_file text,
    source_snapshot_date date,
    pipeline_version text,
    status text DEFAULT 'running'::text NOT NULL,
    duration_seconds double precision,
    notes text,
    mode character varying,
    error_message text
);


ALTER TABLE history.audit_pipeline_runs OWNER TO poi_user;

--
-- Name: audit_pipeline_runs_run_id_seq; Type: SEQUENCE; Schema: history; Owner: poi_user
--

CREATE SEQUENCE history.audit_pipeline_runs_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE history.audit_pipeline_runs_run_id_seq OWNER TO poi_user;

--
-- Name: audit_pipeline_runs_run_id_seq; Type: SEQUENCE OWNED BY; Schema: history; Owner: poi_user
--

ALTER SEQUENCE history.audit_pipeline_runs_run_id_seq OWNED BY history.audit_pipeline_runs.run_id;


--
-- Name: audit_run_stats; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.audit_run_stats (
    run_id integer NOT NULL,
    total_raw integer,
    total_after_filter integer,
    inserted integer,
    updated integer,
    deactivated integer,
    reactivated integer,
    unchanged integer
);


ALTER TABLE history.audit_run_stats OWNER TO poi_user;

--
-- Name: production_poi_history; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.production_poi_history (
    typed_id text,
    osm_id text,
    osm_type text,
    name text,
    fclass text,
    super_category text,
    geom public.geometry(Point,4326),
    lat double precision,
    lon double precision,
    version integer,
    visible boolean,
    valid_from timestamp with time zone,
    valid_to timestamp with time zone,
    valid_range tstzrange,
    matched_tag_key text,
    poi_source text,
    tags_json jsonb,
    dedup_group text,
    is_canonical boolean
);


ALTER TABLE history.production_poi_history OWNER TO poi_user;

--
-- Name: staging_node_tags; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_node_tags (
    node_id bigint NOT NULL,
    version integer NOT NULL,
    key text NOT NULL,
    value text
);


ALTER TABLE history.staging_node_tags OWNER TO poi_user;

--
-- Name: staging_nodes; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_nodes (
    id bigint NOT NULL,
    version integer NOT NULL,
    visible boolean DEFAULT true NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    changeset bigint,
    uid integer,
    username text,
    lat double precision,
    lon double precision
);


ALTER TABLE history.staging_nodes OWNER TO poi_user;

--
-- Name: staging_relation_members; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_relation_members (
    relation_id bigint NOT NULL,
    version integer NOT NULL,
    "position" integer NOT NULL,
    member_type character(1) NOT NULL,
    member_id bigint NOT NULL,
    role text
);


ALTER TABLE history.staging_relation_members OWNER TO poi_user;

--
-- Name: staging_relation_tags; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_relation_tags (
    relation_id bigint NOT NULL,
    version integer NOT NULL,
    key text NOT NULL,
    value text
);


ALTER TABLE history.staging_relation_tags OWNER TO poi_user;

--
-- Name: staging_relations; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_relations (
    id bigint NOT NULL,
    version integer NOT NULL,
    visible boolean DEFAULT true NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    changeset bigint,
    uid integer,
    username text
);


ALTER TABLE history.staging_relations OWNER TO poi_user;

--
-- Name: staging_way_nodes; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_way_nodes (
    way_id bigint NOT NULL,
    version integer NOT NULL,
    "position" integer NOT NULL,
    node_id bigint NOT NULL
);


ALTER TABLE history.staging_way_nodes OWNER TO poi_user;

--
-- Name: staging_way_tags; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_way_tags (
    way_id bigint NOT NULL,
    version integer NOT NULL,
    key text NOT NULL,
    value text
);


ALTER TABLE history.staging_way_tags OWNER TO poi_user;

--
-- Name: staging_ways; Type: TABLE; Schema: history; Owner: poi_user
--

CREATE TABLE history.staging_ways (
    id bigint NOT NULL,
    version integer NOT NULL,
    visible boolean DEFAULT true NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    changeset bigint,
    uid integer,
    username text
);


ALTER TABLE history.staging_ways OWNER TO poi_user;

--
-- Name: properties; Type: TABLE; Schema: production; Owner: poi_user
--

CREATE TABLE production.properties (
    id bigint NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    metadata jsonb,
    db_row_id bigint,
    transaction_id bigint,
    transaction_date timestamp without time zone,
    transaction_year integer,
    transaction_month integer,
    transaction_quarter text,
    asset_price double precision,
    asset_surface double precision,
    asset_psqm double precision,
    asset_rooms double precision,
    asset_floor text,
    asset_type text,
    asset_geometry public.geometry(Point,4326),
    asset_latitude double precision,
    asset_longitude double precision,
    asset_hashed_title text,
    land_hashed_title text,
    land_geometry public.geometry(Geometry,4326),
    ilot_uid text,
    ilot_objectid text,
    ilot_geometry public.geometry(Geometry,4326),
    iris_uid text,
    iris_code text,
    iris_geometry public.geometry(Geometry,4326),
    neighbourhood_uid text,
    neighbour_name text,
    neighbourhood_geometry public.geometry(Geometry,4326),
    district_uid text,
    district_name text,
    district_geometry public.geometry(Geometry,4326)
);


ALTER TABLE production.properties OWNER TO poi_user;

--
-- Name: property_features; Type: TABLE; Schema: production; Owner: poi_user
--

CREATE TABLE production.property_features (
    property_id bigint NOT NULL,
    poi_refreshed_at timestamp with time zone NOT NULL,
    pipeline_version text NOT NULL,
    computed_at timestamp with time zone DEFAULT now() NOT NULL,
    poi_count_1km integer NOT NULL,
    poi_count_400m integer NOT NULL,
    n_categories integer NOT NULL,
    n_poi_types integer NOT NULL,
    entropy double precision NOT NULL,
    entropy_fclass double precision NOT NULL,
    aggregate_score double precision,
    acc_bus_stop boolean NOT NULL,
    acc_pharmacy boolean NOT NULL,
    acc_school boolean NOT NULL,
    acc_hospital boolean NOT NULL,
    acc_supermarket boolean NOT NULL,
    acc_bank boolean NOT NULL,
    acc_atm boolean NOT NULL,
    acc_clinic boolean NOT NULL,
    acc_fuel boolean NOT NULL,
    acc_police boolean NOT NULL,
    acc_park boolean NOT NULL,
    acc_doctors boolean NOT NULL,
    acc_taxi boolean NOT NULL,
    by_category jsonb DEFAULT '{}'::jsonb NOT NULL,
    nearest_km jsonb DEFAULT '{}'::jsonb NOT NULL,
    dist_coast_km double precision,
    land_buffer_fraction_1km double precision,
    transaction_date date,
    poi_source text
);


ALTER TABLE production.property_features OWNER TO poi_user;

--
-- Name: audit_pipeline_runs run_id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.audit_pipeline_runs ALTER COLUMN run_id SET DEFAULT nextval('active.audit_pipeline_runs_run_id_seq'::regclass);


--
-- Name: audit_pois_history id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.audit_pois_history ALTER COLUMN id SET DEFAULT nextval('active.audit_pois_history_id_seq'::regclass);


--
-- Name: categories id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.categories ALTER COLUMN id SET DEFAULT nextval('active.categories_id_seq'::regclass);


--
-- Name: category_mapping id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.category_mapping ALTER COLUMN id SET DEFAULT nextval('active.category_mapping_id_seq'::regclass);


--
-- Name: city_polygons id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.city_polygons ALTER COLUMN id SET DEFAULT nextval('active.city_polygons_id_seq'::regclass);


--
-- Name: inspection_log id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.inspection_log ALTER COLUMN id SET DEFAULT nextval('active.inspection_log_id_seq'::regclass);


--
-- Name: production_pois_current id; Type: DEFAULT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.production_pois_current ALTER COLUMN id SET DEFAULT nextval('active.production_pois_current_id_seq'::regclass);


--
-- Name: coastline id; Type: DEFAULT; Schema: geo; Owner: poi_user
--

ALTER TABLE ONLY geo.coastline ALTER COLUMN id SET DEFAULT nextval('geo.coastline_id_seq'::regclass);


--
-- Name: land id; Type: DEFAULT; Schema: geo; Owner: poi_user
--

ALTER TABLE ONLY geo.land ALTER COLUMN id SET DEFAULT nextval('geo.land_id_seq'::regclass);


--
-- Name: audit_pipeline_runs run_id; Type: DEFAULT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.audit_pipeline_runs ALTER COLUMN run_id SET DEFAULT nextval('history.audit_pipeline_runs_run_id_seq'::regclass);


--
-- Name: audit_pipeline_runs audit_pipeline_runs_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.audit_pipeline_runs
    ADD CONSTRAINT audit_pipeline_runs_pkey PRIMARY KEY (run_id);


--
-- Name: audit_pois_history audit_pois_history_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.audit_pois_history
    ADD CONSTRAINT audit_pois_history_pkey PRIMARY KEY (id);


--
-- Name: categories categories_name_key; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.categories
    ADD CONSTRAINT categories_name_key UNIQUE (name);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: category_mapping category_mapping_fclass_key; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.category_mapping
    ADD CONSTRAINT category_mapping_fclass_key UNIQUE (fclass);


--
-- Name: category_mapping category_mapping_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.category_mapping
    ADD CONSTRAINT category_mapping_pkey PRIMARY KEY (id);


--
-- Name: city_polygons city_polygons_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.city_polygons
    ADD CONSTRAINT city_polygons_pkey PRIMARY KEY (id);


--
-- Name: inspection_log inspection_log_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.inspection_log
    ADD CONSTRAINT inspection_log_pkey PRIMARY KEY (id);


--
-- Name: production_pois_current production_pois_current_osm_id_key; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.production_pois_current
    ADD CONSTRAINT production_pois_current_osm_id_key UNIQUE (osm_id);


--
-- Name: production_pois_current production_pois_current_pkey; Type: CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.production_pois_current
    ADD CONSTRAINT production_pois_current_pkey PRIMARY KEY (id);


--
-- Name: coastline coastline_pkey; Type: CONSTRAINT; Schema: geo; Owner: poi_user
--

ALTER TABLE ONLY geo.coastline
    ADD CONSTRAINT coastline_pkey PRIMARY KEY (id);


--
-- Name: land land_pkey; Type: CONSTRAINT; Schema: geo; Owner: poi_user
--

ALTER TABLE ONLY geo.land
    ADD CONSTRAINT land_pkey PRIMARY KEY (id);


--
-- Name: audit_pipeline_runs audit_pipeline_runs_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.audit_pipeline_runs
    ADD CONSTRAINT audit_pipeline_runs_pkey PRIMARY KEY (run_id);


--
-- Name: staging_node_tags staging_node_tags_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_node_tags
    ADD CONSTRAINT staging_node_tags_pkey PRIMARY KEY (node_id, version, key);


--
-- Name: staging_nodes staging_nodes_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_nodes
    ADD CONSTRAINT staging_nodes_pkey PRIMARY KEY (id, version);


--
-- Name: staging_relation_members staging_relation_members_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_relation_members
    ADD CONSTRAINT staging_relation_members_pkey PRIMARY KEY (relation_id, version, "position");


--
-- Name: staging_relation_tags staging_relation_tags_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_relation_tags
    ADD CONSTRAINT staging_relation_tags_pkey PRIMARY KEY (relation_id, version, key);


--
-- Name: staging_relations staging_relations_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_relations
    ADD CONSTRAINT staging_relations_pkey PRIMARY KEY (id, version);


--
-- Name: staging_way_nodes staging_way_nodes_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_way_nodes
    ADD CONSTRAINT staging_way_nodes_pkey PRIMARY KEY (way_id, version, "position");


--
-- Name: staging_way_tags staging_way_tags_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_way_tags
    ADD CONSTRAINT staging_way_tags_pkey PRIMARY KEY (way_id, version, key);


--
-- Name: staging_ways staging_ways_pkey; Type: CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.staging_ways
    ADD CONSTRAINT staging_ways_pkey PRIMARY KEY (id, version);


--
-- Name: properties properties_pkey; Type: CONSTRAINT; Schema: production; Owner: poi_user
--

ALTER TABLE ONLY production.properties
    ADD CONSTRAINT properties_pkey PRIMARY KEY (id);


--
-- Name: property_features property_features_pkey; Type: CONSTRAINT; Schema: production; Owner: poi_user
--

ALTER TABLE ONLY production.property_features
    ADD CONSTRAINT property_features_pkey PRIMARY KEY (property_id);


--
-- Name: idx_catmap_category; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_catmap_category ON active.category_mapping USING btree (category_id);


--
-- Name: idx_catmap_fclass; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_catmap_fclass ON active.category_mapping USING btree (fclass);


--
-- Name: idx_city_geom; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_city_geom ON active.city_polygons USING gist (geom);


--
-- Name: idx_city_name; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_city_name ON active.city_polygons USING btree (name);


--
-- Name: idx_history_change; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_history_change ON active.audit_pois_history USING btree (change_type);


--
-- Name: idx_history_osm_id; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_history_osm_id ON active.audit_pois_history USING btree (osm_id);


--
-- Name: idx_history_run_id; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_history_run_id ON active.audit_pois_history USING btree (run_id);


--
-- Name: idx_inspection_log_fclass; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_inspection_log_fclass ON active.inspection_log USING btree (fclass);


--
-- Name: idx_inspection_log_time; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_inspection_log_time ON active.inspection_log USING btree (logged_at DESC);


--
-- Name: idx_prod_content_hash; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_content_hash ON active.production_pois_current USING btree (content_hash);


--
-- Name: idx_prod_fclass; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_fclass ON active.production_pois_current USING btree (fclass);


--
-- Name: idx_prod_geom; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_geom ON active.production_pois_current USING gist (geom);


--
-- Name: idx_prod_geom_geog; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_geom_geog ON active.production_pois_current USING gist (((geom)::public.geography));


--
-- Name: idx_prod_is_active; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_is_active ON active.production_pois_current USING btree (is_active);


--
-- Name: idx_prod_name; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_name ON active.production_pois_current USING btree (name);


--
-- Name: idx_prod_super_category; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_prod_super_category ON active.production_pois_current USING btree (super_category);


--
-- Name: idx_stage_hash; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_stage_hash ON active.staging_pois_stage USING btree (content_hash);


--
-- Name: idx_stage_osm_id; Type: INDEX; Schema: active; Owner: poi_user
--

CREATE INDEX idx_stage_osm_id ON active.staging_pois_stage USING btree (osm_id);


--
-- Name: idx_coastline_geom; Type: INDEX; Schema: geo; Owner: poi_user
--

CREATE INDEX idx_coastline_geom ON geo.coastline USING gist (geom);


--
-- Name: idx_geo_coastline_geom; Type: INDEX; Schema: geo; Owner: poi_user
--

CREATE INDEX idx_geo_coastline_geom ON geo.coastline USING gist (geom);


--
-- Name: idx_geo_land_geom; Type: INDEX; Schema: geo; Owner: poi_user
--

CREATE INDEX idx_geo_land_geom ON geo.land USING gist (geom);


--
-- Name: idx_land_geom; Type: INDEX; Schema: geo; Owner: poi_user
--

CREATE INDEX idx_land_geom ON geo.land USING gist (geom);


--
-- Name: idx_node_tags_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_node_tags_id ON history.staging_node_tags USING btree (node_id, version);


--
-- Name: idx_node_tags_key; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_node_tags_key ON history.staging_node_tags USING btree (key);


--
-- Name: idx_nodes_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_nodes_id ON history.staging_nodes USING btree (id);


--
-- Name: idx_nodes_ts; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_nodes_ts ON history.staging_nodes USING btree ("timestamp");


--
-- Name: idx_phist_dedup_group; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_dedup_group ON history.production_poi_history USING btree (dedup_group);


--
-- Name: idx_phist_fclass; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_fclass ON history.production_poi_history USING btree (fclass);


--
-- Name: idx_phist_geom_geog; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_geom_geog ON history.production_poi_history USING gist (((geom)::public.geography));


--
-- Name: idx_phist_is_canonical; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_is_canonical ON history.production_poi_history USING btree (is_canonical);


--
-- Name: idx_phist_osm_type; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_osm_type ON history.production_poi_history USING btree (osm_type);


--
-- Name: idx_phist_super_category; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_super_category ON history.production_poi_history USING btree (super_category);


--
-- Name: idx_phist_typed_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_typed_id ON history.production_poi_history USING btree (typed_id);


--
-- Name: idx_phist_valid_from; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_valid_from ON history.production_poi_history USING btree (valid_from);


--
-- Name: idx_phist_valid_range; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_phist_valid_range ON history.production_poi_history USING gist (valid_range);


--
-- Name: idx_rel_members_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_rel_members_id ON history.staging_relation_members USING btree (relation_id, version);


--
-- Name: idx_rel_members_member; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_rel_members_member ON history.staging_relation_members USING btree (member_type, member_id);


--
-- Name: idx_rel_tags_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_rel_tags_id ON history.staging_relation_tags USING btree (relation_id, version);


--
-- Name: idx_rel_tags_key; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_rel_tags_key ON history.staging_relation_tags USING btree (key);


--
-- Name: idx_rels_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_rels_id ON history.staging_relations USING btree (id);


--
-- Name: idx_rels_ts; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_rels_ts ON history.staging_relations USING btree ("timestamp");


--
-- Name: idx_way_nodes_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_way_nodes_id ON history.staging_way_nodes USING btree (way_id, version);


--
-- Name: idx_way_nodes_node; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_way_nodes_node ON history.staging_way_nodes USING btree (node_id);


--
-- Name: idx_way_tags_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_way_tags_id ON history.staging_way_tags USING btree (way_id, version);


--
-- Name: idx_way_tags_key; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_way_tags_key ON history.staging_way_tags USING btree (key);


--
-- Name: idx_ways_id; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_ways_id ON history.staging_ways USING btree (id);


--
-- Name: idx_ways_ts; Type: INDEX; Schema: history; Owner: poi_user
--

CREATE INDEX idx_ways_ts ON history.staging_ways USING btree ("timestamp");


--
-- Name: idx_properties_transaction_date; Type: INDEX; Schema: production; Owner: poi_user
--

CREATE INDEX idx_properties_transaction_date ON production.properties USING btree (transaction_date);


--
-- Name: idx_properties_transaction_id; Type: INDEX; Schema: production; Owner: poi_user
--

CREATE INDEX idx_properties_transaction_id ON production.properties USING btree (transaction_id);


--
-- Name: idx_property_features_poi_refreshed_at; Type: INDEX; Schema: production; Owner: poi_user
--

CREATE INDEX idx_property_features_poi_refreshed_at ON production.property_features USING btree (poi_refreshed_at);


--
-- Name: audit_pois_history audit_pois_history_run_id_fkey; Type: FK CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.audit_pois_history
    ADD CONSTRAINT audit_pois_history_run_id_fkey FOREIGN KEY (run_id) REFERENCES active.audit_pipeline_runs(run_id);


--
-- Name: audit_run_stats audit_run_stats_run_id_fkey; Type: FK CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.audit_run_stats
    ADD CONSTRAINT audit_run_stats_run_id_fkey FOREIGN KEY (run_id) REFERENCES active.audit_pipeline_runs(run_id);


--
-- Name: category_mapping category_mapping_category_id_fkey; Type: FK CONSTRAINT; Schema: active; Owner: poi_user
--

ALTER TABLE ONLY active.category_mapping
    ADD CONSTRAINT category_mapping_category_id_fkey FOREIGN KEY (category_id) REFERENCES active.categories(id) ON DELETE RESTRICT;


--
-- Name: audit_run_stats audit_run_stats_run_id_fkey; Type: FK CONSTRAINT; Schema: history; Owner: poi_user
--

ALTER TABLE ONLY history.audit_run_stats
    ADD CONSTRAINT audit_run_stats_run_id_fkey FOREIGN KEY (run_id) REFERENCES history.audit_pipeline_runs(run_id);


--
-- Name: property_features property_features_property_id_fkey; Type: FK CONSTRAINT; Schema: production; Owner: poi_user
--

ALTER TABLE ONLY production.property_features
    ADD CONSTRAINT property_features_property_id_fkey FOREIGN KEY (property_id) REFERENCES production.properties(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict iW3BAQoJhYBPiuWBQIEPwSX6Kc1rBA8Sde0dOTgRSKLmfvyl2ZzmZfiEEtKRA6O

