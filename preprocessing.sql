/*
 * update distances
 */
WITH
segment_node AS (
    SELECT segment.id, segment.way_id, segment.idx, node.loc
    FROM segment JOIN node ON node.id = segment.node_id
),
dist_ AS (
    SELECT b.id AS segment_id,
           ST_Distance(a.loc, b.loc) AS dist,
           SUM(ST_Distance(a.loc, b.loc))
               OVER(PARTITION BY b.way_id ORDER BY b.idx) AS cdist
    FROM segment_node AS a, segment_node AS b
    WHERE (a.way_id = b.way_id AND a.idx + 1 = b.idx)
)

UPDATE segment
SET dist = 0, cdist = 0
WHERE idx = 0

UPDATE segment
SET dist = d.dist, cdist = d.cdist
FROM dist_ as d
WHERE segment.id = d.segment_id

/*
 * update number of ways associated with each node
 */
WITH way_count AS (
    SELECT node_id, COUNT(way_id) AS num_ways
    FROM segment
    GROUP BY node_id
)

UPDATE node
SET num_ways = way_count.num_ways
FROM way_count
WHERE node.id = way_count.node_id

UPDATE node
SET num_ways = 0
WHERE num_ways IS NULL
